"""Exact capacity-state dynamic programming for supplied daily skater points."""

from collections import Counter
from decimal import (
    MAX_EMAX,
    MIN_EMIN,
    Context,
    Decimal,
    DecimalException,
    Inexact,
    localcontext,
)
from math import prod
from typing import NamedTuple

from fantasy_gm.domain.lineup import (
    DailyLineupResult,
    LineupAssignment,
    LineupChange,
    SkaterPosition,
    SkaterProjection,
    SlotCapacity,
)


class UnsupportedLineupError(ValueError):
    """The supplied problem is ambiguous or outside this solver's support."""


class InfeasibleLineupError(ValueError):
    """The baseline or fixed assignments violate the supplied constraints."""


class _Candidate(NamedTuple):
    points: Decimal
    changes: int
    assignments: tuple[tuple[str, SkaterPosition], ...]


def _better(candidate: _Candidate, previous: _Candidate) -> bool:
    if candidate.points != previous.points:
        return candidate.points > previous.points
    return (candidate.changes, candidate.assignments) < (
        previous.changes,
        previous.assignments,
    )


def _assignments_by_player(
    assignments: tuple[LineupAssignment, ...],
    players: dict[str, SkaterProjection],
    capacities: dict[SkaterPosition, int],
) -> dict[str, SkaterPosition]:
    result: dict[str, SkaterPosition] = {}
    counts: Counter[SkaterPosition] = Counter()
    for item in assignments:
        if item.player_id in result:
            raise InfeasibleLineupError("A lineup cannot assign a player twice")
        if item.player_id not in players:
            raise UnsupportedLineupError("Assignment references an unknown player")
        if item.position not in players[item.player_id].eligible_positions:
            raise InfeasibleLineupError("Assignment violates supplied eligibility")
        counts[item.position] += 1
        if counts[item.position] > capacities.get(item.position, 0):
            raise InfeasibleLineupError("Assignment exceeds supplied slot capacity")
        result[item.player_id] = item.position
    return result


def optimize_daily_skaters(
    players: tuple[SkaterProjection, ...],
    slots: tuple[SlotCapacity, ...],
    *,
    current: tuple[LineupAssignment, ...] = (),
    locked: tuple[LineupAssignment, ...] = (),
) -> DailyLineupResult:
    """Joint maximum, then fewest changed players, lexical assignment order.

    Current may be partial but must respect eligibility/capacity. Locks constrain
    the result independently of current. Every unlocked slot is optional. Both
    projected total and improvement describe supplied assumptions only.
    """
    exponents = [p.projected_points.as_tuple().exponent for p in players]
    if any(not isinstance(exponent, int) for exponent in exponents):
        raise UnsupportedLineupError("Projections must be finite Decimals")
    precision = (
        max(
            1,
            max(p.projected_points.adjusted() for p in players)
            - min(int(e) for e in exponents)
            + len(str(len(players)))
            + 2,
        )
        if players
        else 1
    )
    if precision > 10_000:
        raise UnsupportedLineupError(
            "Projection precision span exceeds supported limit of 10000"
        )
    # Do not let a caller's precision, rounding or traps change the optimum.
    arithmetic = Context(prec=precision, Emax=MAX_EMAX, Emin=MIN_EMIN)
    arithmetic.traps[Inexact] = True
    with localcontext(arithmetic):
        try:
            return _optimize(players, slots, current, locked)
        except DecimalException as error:
            raise UnsupportedLineupError(
                "Projection numeric range is unsupported"
            ) from error


def _optimize(
    players: tuple[SkaterProjection, ...],
    slots: tuple[SlotCapacity, ...],
    current: tuple[LineupAssignment, ...],
    locked: tuple[LineupAssignment, ...],
) -> DailyLineupResult:
    by_id = {p.player_id: p for p in players}
    capacities = {s.position: s.capacity for s in slots}
    if len(by_id) != len(players):
        raise UnsupportedLineupError("Duplicate player identifiers")
    if len(capacities) != len(slots):
        raise UnsupportedLineupError("Duplicate slot types")
    if any(
        len(set(p.eligible_positions)) != len(p.eligible_positions) for p in players
    ):
        raise UnsupportedLineupError("Duplicate eligible positions")
    baseline = _assignments_by_player(current, by_id, capacities)
    fixed = _assignments_by_player(locked, by_id, capacities)
    positions = tuple(sorted(capacities))
    limits = tuple(min(capacities[p], len(players)) for p in positions)
    if prod(n + 1 for n in limits) > 100_000:
        raise UnsupportedLineupError(
            "Capacity state space exceeds supported limit of 100000"
        )
    states = {tuple(0 for _ in positions): _Candidate(Decimal(0), 0, ())}
    for player in sorted(players, key=lambda p: p.player_id):
        following = {
            occupied: _Candidate(
                candidate.points,
                candidate.changes + int(player.player_id in baseline),
                candidate.assignments,
            )
            for occupied, candidate in states.items()
            if player.player_id not in fixed
        }
        for occupied, candidate in states.items():
            for index, position in enumerate(positions):
                if (
                    position not in player.eligible_positions
                    or occupied[index] >= limits[index]
                    or (
                        player.player_id in fixed
                        and position != fixed[player.player_id]
                    )
                ):
                    continue
                counts = list(occupied)
                counts[index] += 1
                key = tuple(counts)
                choice = _Candidate(
                    candidate.points + player.projected_points,
                    candidate.changes + int(baseline.get(player.player_id) != position),
                    (*candidate.assignments, (player.player_id, position)),
                )
                if key not in following or _better(choice, following[key]):
                    following[key] = choice
        states = following
    if not states:
        raise InfeasibleLineupError("Locked assignments are infeasible")
    best = next(iter(states.values()))
    for candidate in states.values():
        if _better(candidate, best):
            best = candidate
    assignments = tuple(
        LineupAssignment(player_id=key, position=position)
        for key, position in best.assignments
    )
    chosen = _assignments_by_player(assignments, by_id, capacities)
    if any(chosen.get(key) != position for key, position in fixed.items()):
        raise InfeasibleLineupError("No legal lineup respects the fixed assignments")
    baseline_points = sum((by_id[key].projected_points for key in baseline), Decimal(0))
    changes = tuple(
        LineupChange(
            player_id=key,
            from_position=baseline.get(key),
            to_position=chosen.get(key),
            projected_points=by_id[key].projected_points,
            reason=(
                f"{baseline.get(key) or 'bench'} -> {chosen.get(key) or 'bench'}. "
                f"Supplied projection {by_id[key].projected_points}; joint lineup "
                f"total {best.points} versus baseline {baseline_points}. "
                "Selection uses only supplied eligibility, capacities and locks."
            ),
        )
        for key in sorted(by_id)
        if baseline.get(key) != chosen.get(key)
    )
    return DailyLineupResult(
        assignments=assignments,
        benched_player_ids=tuple(sorted(by_id.keys() - chosen.keys())),
        projected_points=best.points,
        baseline_points=baseline_points,
        estimated_improvement=best.points - baseline_points,
        changes=changes,
    )
