"""Pure local-calendar analysis of qualified or explicitly partial schedules."""

from datetime import date, timedelta
from zoneinfo import ZoneInfo

from fantasy_gm.domain.schedule import (
    GameState,
    GameType,
    ScheduledGame,
    ScheduleReport,
    ScheduleSnapshot,
    TeamScheduleSummary,
)


def validate_window(start: date, end: date) -> None:
    if start > end or (end - start).days >= 31 or start == date.min or end == date.max:
        raise ValueError("INPUT_ERROR")


def _dates(start: date, end: date) -> frozenset[date]:
    return frozenset(start + timedelta(days=i) for i in range((end - start).days + 1))


def _normal(game: ScheduledGame) -> bool:
    return (
        game.schedule_normal
        and game.state
        in (
            GameState.SCHEDULED,
            GameState.IN_PROGRESS,
            GameState.COMPLETED,
        )
        and game.game_type != GameType.UNKNOWN
        and game.start_time_utc is not None
    )


def analyze_schedule(
    snapshot: ScheduleSnapshot,
    *,
    start: date,
    end: date,
    timezone: ZoneInfo,
    game_type: GameType | None = GameType.REGULAR,
) -> ScheduleReport:
    validate_window(start, end)
    qualified = (
        snapshot.cohort_verified
        and snapshot.coverage_contract_verified
        and snapshot.coverage_timezone == timezone.key
        and not snapshot.issues
        and bool(snapshot.teams)
    )
    counts_covered = qualified and _dates(start, end) <= snapshot.covered_dates
    context_covered = (
        qualified
        and _dates(start - timedelta(days=1), end + timedelta(days=1))
        <= snapshot.covered_dates
    )
    # Identical observations collapse without losing conflicts (model validates).
    games = tuple({g.provider_game_id: g for g in snapshot.games}.values())
    summaries: list[TeamScheduleSummary] = []
    for team in snapshot.teams:
        normal: list[tuple[date, ScheduledGame]] = []
        shown: list[ScheduledGame] = []
        counts = {
            state: 0
            for state in (
                GameState.SCHEDULED,
                GameState.IN_PROGRESS,
                GameState.COMPLETED,
            )
        }
        uncertain = unplaced = context_uncertain = 0
        for game in games:
            if team not in (game.home, game.away):
                continue
            if game_type is not None and game.game_type not in (
                game_type,
                GameType.UNKNOWN,
            ):
                continue
            if game.start_time_utc is None:
                # Unqualified source dates cannot safely scope a missing instant out.
                unplaced += 1
                continue
            local = game.start_time_utc.astimezone(timezone).date()
            if start <= local <= end:
                shown.append(game)
                if _normal(game):
                    counts[game.state] += 1
                else:
                    uncertain += 1
            if start - timedelta(days=1) <= local <= end + timedelta(days=1):
                if _normal(game):
                    normal.append((local, game))
                else:
                    context_uncertain += 1
        normal.sort(key=lambda item: (item[0], item[1].provider_game_id))
        pairs = tuple(
            (first.provider_game_id, second.provider_game_id)
            for day1, first in normal
            for day2, second in normal
            if day2 - day1 == timedelta(days=1)
            and (start <= day1 <= end or start <= day2 <= end)
        )
        summaries.append(
            TeamScheduleSummary(
                team=team,
                scheduled=counts[GameState.SCHEDULED],
                in_progress=counts[GameState.IN_PROGRESS],
                completed=counts[GameState.COMPLETED],
                uncertain_dated=uncertain,
                unplaced=unplaced,
                games=tuple(
                    sorted(
                        shown,
                        key=lambda g: (
                            g.start_time_utc.isoformat() if g.start_time_utc else "",
                            g.provider_game_id,
                        ),
                    )
                ),
                back_to_back_pairs=pairs,
                count_complete=counts_covered and not uncertain and not unplaced,
                back_to_back_complete=context_covered
                and not context_uncertain
                and not unplaced,
            )
        )
    ranking = bool(summaries) and all(s.count_complete for s in summaries)
    summaries.sort(key=lambda s: (-s.total if ranking else 0, s.team.abbreviation))
    return ScheduleReport(
        summaries=tuple(summaries),
        ranking_available=ranking,
        issues=snapshot.issues,
    )
