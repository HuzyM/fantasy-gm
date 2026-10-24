"""Fictional skaters and supplied projections only; no prediction claims."""

from decimal import MIN_EMIN, Decimal, Inexact, localcontext
from fractions import Fraction
from itertools import permutations, product
from random import Random

import pytest
from pydantic import ValidationError

from fantasy_gm.domain.lineup import LineupAssignment, SkaterProjection, SlotCapacity
from fantasy_gm.optimizer.daily_skaters import (
    InfeasibleLineupError,
    UnsupportedLineupError,
    optimize_daily_skaters,
)


def player(key: str, points: str, *positions: str) -> SkaterProjection:
    return SkaterProjection.model_validate(
        {
            "player_id": key,
            "projected_points": Decimal(points),
            "eligible_positions": positions,
        }
    )


def assignment(key: str, position: str) -> LineupAssignment:
    return LineupAssignment.model_validate({"player_id": key, "position": position})


def test_joint_assignment_beats_greedy_position_choices() -> None:
    players = (
        player("fiction-a", "10", "C", "LW"),
        player("fiction-b", "9", "C"),
        player("fiction-c", "8", "LW", "UTIL"),
        player("fiction-d", "7", "RW", "UTIL"),
        player("fiction-e", "6", "C", "RW"),
        player("fiction-f", "5", "LW", "RW", "UTIL"),
        player("fiction-g", "4", "C", "LW", "UTIL"),
        player("fiction-h", "3", "LW", "RW", "UTIL"),
    )
    slots = tuple(
        SlotCapacity.model_validate({"position": position, "capacity": 1})
        for position in ("C", "LW", "RW", "UTIL")
    )
    current = (
        assignment("fiction-a", "C"),
        assignment("fiction-c", "LW"),
        assignment("fiction-d", "RW"),
        assignment("fiction-f", "UTIL"),
    )
    result = optimize_daily_skaters(players, slots, current=current)
    assert result.assignments == (
        assignment("fiction-a", "LW"),
        assignment("fiction-b", "C"),
        assignment("fiction-c", "UTIL"),
        assignment("fiction-d", "RW"),
    )
    assert result.projected_points == Decimal("34")
    assert result.baseline_points == Decimal("30")
    assert result.estimated_improvement == Decimal("4")
    assert exhaustive_oracle(players, slots, current) == (
        Fraction(34),
        (
            ("fiction-a", "LW"),
            ("fiction-b", "C"),
            ("fiction-c", "UTIL"),
            ("fiction-d", "RW"),
        ),
    )
    assert result.benched_player_ids == (
        "fiction-e",
        "fiction-f",
        "fiction-g",
        "fiction-h",
    )
    assert {(c.player_id, c.from_position, c.to_position) for c in result.changes} == {
        ("fiction-a", "C", "LW"),
        ("fiction-b", None, "C"),
        ("fiction-c", "LW", "UTIL"),
        ("fiction-f", "UTIL", None),
    }


def test_equal_total_preserves_current_lineup_even_for_zero_points() -> None:
    players = (player("fiction-a", "0", "C", "UTIL"), player("fiction-z", "0", "C"))
    slots = (
        SlotCapacity(position="C", capacity=1),
        SlotCapacity(position="UTIL", capacity=1),
    )
    current = (assignment("fiction-z", "C"),)
    result = optimize_daily_skaters(players, slots, current=current)
    assert result.assignments == current
    assert result.changes == ()
    assert result.estimated_improvement == 0


def test_fixed_lock_is_respected_even_when_it_forces_a_negative_total() -> None:
    players = (player("fiction-a", "10", "C"), player("fiction-b", "-2", "C", "UTIL"))
    slots = (
        SlotCapacity(position="C", capacity=1),
        SlotCapacity(position="UTIL", capacity=1),
    )
    current = (assignment("fiction-a", "C"),)
    locked = (assignment("fiction-b", "C"),)
    result = optimize_daily_skaters(players, slots, current=current, locked=locked)
    assert result.assignments == locked
    assert result.projected_points == Decimal("-2")
    assert result.estimated_improvement == Decimal("-12")


def test_decimal_ranking_and_delta_are_exact_independent_of_callers_context() -> None:
    players = (
        player("fiction-a", "1.00000000000000000000000000001", "C"),
        player("fiction-b", "1.00000000000000000000000000002", "C"),
    )
    slots = (SlotCapacity(position="C", capacity=1),)
    with localcontext() as context:
        context.prec = 4
        context.traps[Inexact] = True
        result = optimize_daily_skaters(
            players, slots, current=(assignment("fiction-a", "C"),)
        )
        assert context.prec == 4
    assert result.assignments == (assignment("fiction-b", "C"),)
    assert result.projected_points == Decimal("1.00000000000000000000000000002")
    assert result.estimated_improvement == Decimal("0.00000000000000000000000000001")


def exhaustive_oracle(
    players: tuple[SkaterProjection, ...],
    slots: tuple[SlotCapacity, ...],
    current: tuple[LineupAssignment, ...] = (),
    locked: tuple[LineupAssignment, ...] = (),
) -> tuple[Fraction, tuple[tuple[str, str], ...]] | None:
    """Enumerate occupants of physical slots, independently of the solver's DP.

    Fraction provides an independent exact numeric oracle. No solver helpers or
    capacity-state pruning are used, including for the declared tie policy.
    """
    physical_slots = tuple(
        slot.position for slot in slots for _ in range(slot.capacity)
    )
    by_id = {p.player_id: p for p in players}
    before = {a.player_id: a.position for a in current}
    best: tuple[Fraction, int, tuple[tuple[str, str], ...]] | None = None
    for occupants in product((None, *by_id), repeat=len(physical_slots)):
        starters = tuple(key for key in occupants if key is not None)
        if len(set(starters)) != len(starters):
            continue
        if any(
            key is not None and position not in by_id[key].eligible_positions
            for key, position in zip(occupants, physical_slots, strict=True)
        ):
            continue
        after = {
            key: position
            for key, position in zip(occupants, physical_slots, strict=True)
            if key is not None
        }
        if any(after.get(a.player_id) != a.position for a in locked):
            continue
        total = sum(
            (Fraction(by_id[key].projected_points) for key in starters), Fraction()
        )
        changes = sum(before.get(key) != after.get(key) for key in by_id)
        candidate = (-total, changes, tuple(sorted(after.items())))
        if best is None or candidate < best:
            best = candidate
    return None if best is None else (-best[0], best[2])


def test_seeded_cases_match_independent_exhaustive_oracle() -> None:
    rng = Random(20261024)
    for case in range(100):
        players = tuple(
            player(
                f"fiction-{i}",
                rng.choice(("-3", "-0.5", "0", "1", "2", "2.5", "7.25")),
                *rng.sample(("C", "LW", "RW", "UTIL"), rng.randint(1, 4)),
            )
            for i in range(6 + case % 2)
        )
        slots = (
            SlotCapacity(position="C", capacity=1 + int(case % 3 == 0)),
            SlotCapacity(position="LW", capacity=1),
            SlotCapacity(position="UTIL", capacity=1),
        )
        current_list: list[LineupAssignment] = []
        available = list(players)
        for slot in slots:
            for _ in range(slot.capacity):
                eligible = [
                    p for p in available if slot.position in p.eligible_positions
                ]
                if eligible and rng.randrange(2):
                    selected = rng.choice(eligible)
                    current_list.append(assignment(selected.player_id, slot.position))
                    available.remove(selected)
        current = tuple(current_list)
        locked = current[::2] if case % 2 else ()
        expected = exhaustive_oracle(players, slots, current, locked)
        assert expected is not None
        result = optimize_daily_skaters(players, slots, current=current, locked=locked)
        assert Fraction(result.projected_points) == expected[0], case
        assert (
            tuple((a.player_id, a.position) for a in result.assignments) == expected[1]
        ), case
        baseline = sum(
            (
                Fraction(p.projected_points)
                for p in players
                if any(a.player_id == p.player_id for a in current)
            ),
            Fraction(),
        )
        assert Fraction(result.estimated_improvement) == expected[0] - baseline, case
        chosen = {a.player_id for a in result.assignments}
        assert chosen.isdisjoint(result.benched_player_ids), case
        assert chosen | set(result.benched_player_ids) == {
            p.player_id for p in players
        }, case
        assert all(a in result.assignments for a in locked), case
        assert result == optimize_daily_skaters(
            tuple(reversed(players)),
            tuple(reversed(slots)),
            current=tuple(reversed(current)),
            locked=tuple(reversed(locked)),
        ), case


def test_equal_positive_lineups_have_stable_assignments_for_every_input_order() -> None:
    players = tuple(
        player(key, "5", "C", "UTIL") for key in ("fiction-a", "fiction-b", "fiction-c")
    )
    slots = (
        SlotCapacity(position="C", capacity=1),
        SlotCapacity(position="UTIL", capacity=1),
    )
    for ordered in permutations(players):
        result = optimize_daily_skaters(ordered, slots)
        assert result.assignments == (
            assignment("fiction-a", "C"),
            assignment("fiction-b", "UTIL"),
        )
    current = (assignment("fiction-b", "C"), assignment("fiction-a", "UTIL"))
    result = optimize_daily_skaters(players, slots, current=current)
    assert set(result.assignments) == set(current)
    assert result.changes == ()


def test_optional_slots_do_not_require_negative_or_zero_new_starters() -> None:
    players = (
        player("fiction-a", "4", "C"),
        player("fiction-b", "-1", "RW"),
        player("fiction-c", "0", "UTIL"),
    )
    slots = (
        SlotCapacity(position="C", capacity=2),
        SlotCapacity(position="RW", capacity=2),
        SlotCapacity(position="UTIL", capacity=2),
    )
    result = optimize_daily_skaters(players, slots)
    assert result.assignments == (assignment("fiction-a", "C"),)
    assert result.projected_points == 4
    assert result.benched_player_ids == ("fiction-b", "fiction-c")
    result = optimize_daily_skaters(
        players, slots, current=(assignment("fiction-b", "RW"),)
    )
    assert result.estimated_improvement == 5


def test_utility_requires_explicit_eligibility() -> None:
    result = optimize_daily_skaters(
        (player("fiction-a", "10", "C"),), (SlotCapacity(position="UTIL", capacity=1),)
    )
    assert result.assignments == ()
    assert result.benched_player_ids == ("fiction-a",)


@pytest.mark.parametrize("position", ("C", "LW", "RW", "D", "F", "W", "UTIL"))
def test_each_supported_skater_slot_uses_only_explicit_eligibility(
    position: str,
) -> None:
    slots = (SlotCapacity.model_validate({"position": position, "capacity": 1}),)
    result = optimize_daily_skaters((player("fiction-a", "2.5", position),), slots)
    assert result.assignments == (assignment("fiction-a", position),)
    assert result.projected_points == Decimal("2.5")


@pytest.mark.parametrize("points", ("NaN", "sNaN", "Infinity", "-Infinity"))
def test_non_finite_projection_is_rejected(points: str) -> None:
    with pytest.raises(ValidationError):
        player("fiction-a", points, "C")


@pytest.mark.parametrize("positions", ((), ("G",), ("BN",), ("IR",), ("c",)))
def test_empty_or_unsupported_eligibility_is_rejected(
    positions: tuple[str, ...],
) -> None:
    with pytest.raises(ValidationError):
        player("fiction-a", "1", *positions)


@pytest.mark.parametrize("capacity", (-1, 1.5, True, "1"))
def test_invalid_capacity_is_rejected(capacity: object) -> None:
    with pytest.raises(ValidationError):
        SlotCapacity.model_validate({"position": "C", "capacity": capacity})


def test_unsupported_slots_non_decimal_points_and_extra_inputs_are_rejected() -> None:
    with pytest.raises(ValidationError):
        SlotCapacity.model_validate({"position": "G", "capacity": 1})
    for points in (1.5, 1, "1.5"):
        with pytest.raises(ValidationError):
            SkaterProjection.model_validate(
                {
                    "player_id": "fiction-a",
                    "projected_points": points,
                    "eligible_positions": ("C",),
                }
            )
    with pytest.raises(ValidationError):
        SkaterProjection.model_validate(
            {
                "player_id": "fiction-a",
                "projected_points": Decimal(1),
                "eligible_positions": ("C",),
                "goalie": True,
            }
        )
    with pytest.raises(ValidationError):
        player("  ", "1", "C")


def test_duplicate_players_slots_and_eligibility_are_rejected() -> None:
    p = player("fiction-a", "1", "C")
    slot = SlotCapacity(position="C", capacity=1)
    with pytest.raises(ValueError, match="Duplicate player"):
        optimize_daily_skaters((p, p), (slot,))
    with pytest.raises(ValueError, match="Duplicate slot"):
        optimize_daily_skaters((p,), (slot, slot))
    with pytest.raises(ValueError, match="Duplicate eligible"):
        optimize_daily_skaters((player("fiction-a", "1", "C", "C"),), (slot,))


@pytest.mark.parametrize("field", ("current", "locked"))
@pytest.mark.parametrize(
    "items, message",
    (
        ((assignment("missing", "C"),), "unknown player"),
        ((assignment("fiction-a", "RW"),), "eligibility"),
        ((assignment("fiction-a", "C"), assignment("fiction-a", "UTIL")), "twice"),
        ((assignment("fiction-a", "C"), assignment("fiction-b", "C")), "capacity"),
    ),
)
def test_invalid_baseline_or_impossible_locks_are_rejected(
    field: str,
    items: tuple[LineupAssignment, ...],
    message: str,
) -> None:
    players = (
        player("fiction-a", "1", "C", "UTIL"),
        player("fiction-b", "2", "C", "UTIL"),
    )
    slots = (
        SlotCapacity(position="C", capacity=1),
        SlotCapacity(position="UTIL", capacity=1),
    )
    with pytest.raises(ValueError, match=message):
        optimize_daily_skaters(
            players,
            slots,
            current=items if field == "current" else (),
            locked=items if field == "locked" else (),
        )


def test_assignment_to_absent_or_zero_capacity_slot_is_rejected() -> None:
    players = (player("fiction-a", "1", "C"),)
    for slots in ((), (SlotCapacity(position="C", capacity=0),)):
        with pytest.raises(ValueError, match="capacity"):
            optimize_daily_skaters(
                players, slots, locked=(assignment("fiction-a", "C"),)
            )


def test_empty_inputs_and_zero_capacity_are_valid_empty_lineups() -> None:
    assert optimize_daily_skaters((), ()).projected_points == 0
    players = (player("fiction-a", "5", "C"),)
    for slots in ((), (SlotCapacity(position="C", capacity=0),)):
        result = optimize_daily_skaters(players, slots)
        assert result.assignments == ()
        assert result.benched_player_ids == ("fiction-a",)
        assert result.changes == ()


def test_oversized_state_space_and_numeric_span_are_explicitly_unsupported() -> None:
    positions = ("C", "LW", "RW", "D", "F", "W", "UTIL")
    players = tuple(player(f"fiction-{i}", "1", *positions) for i in range(12))
    slots = tuple(
        SlotCapacity.model_validate({"position": p, "capacity": 8}) for p in positions
    )
    with pytest.raises(ValueError, match="state space"):
        optimize_daily_skaters(players, slots)
    with pytest.raises(ValueError, match="precision span"):
        optimize_daily_skaters(
            (player("fiction-a", "1E10001", "C"), player("fiction-b", "0.1", "C")), ()
        )


def test_unrepresentable_decimal_total_rejects_instead_of_silently_underflowing() -> (
    None
):
    tiny = SkaterProjection(
        player_id="fiction-tiny",
        projected_points=Decimal((0, (1,), MIN_EMIN - 100)),
        eligible_positions=("C",),
    )
    with pytest.raises(ValueError, match="numeric range"):
        optimize_daily_skaters((tiny,), (SlotCapacity(position="C", capacity=1),))


def test_infeasible_and_unsupported_are_distinct_error_categories() -> None:
    players = (player("fiction-a", "1", "C"),)
    slot = SlotCapacity(position="C", capacity=1)
    with pytest.raises(InfeasibleLineupError):
        optimize_daily_skaters(players, (), locked=(assignment("fiction-a", "C"),))
    with pytest.raises(UnsupportedLineupError):
        optimize_daily_skaters(players, (slot, slot))


@pytest.mark.parametrize("fixed, total", ((False, "9"), (True, "6")))
def test_opt_001_hand_oracles(fixed: bool, total: str) -> None:
    players = (
        player("fiction-a", "5", "C", "LW"),
        player("fiction-b", "4", "C"),
        player("fiction-c", "1", "LW"),
    )
    slots = (
        SlotCapacity(position="C", capacity=1),
        SlotCapacity(position="LW", capacity=1),
    )
    locked = (assignment("fiction-a", "C"),) if fixed else ()
    expected = exhaustive_oracle(players, slots, locked=locked)
    assert expected is not None
    assert expected[0] == Fraction(total)
    result = optimize_daily_skaters(players, slots, locked=locked)
    assert result.projected_points == Decimal(total)
    assert tuple((a.player_id, a.position) for a in result.assignments) == expected[1]
