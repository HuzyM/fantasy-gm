"""Invented clubs/games only; hand-derived schedule expectations."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError

from fantasy_gm.domain.schedule import (
    GameState,
    GameType,
    ScheduledGame,
    ScheduleSnapshot,
    ScheduleTeam,
)
from fantasy_gm.sports.nhl.schedule import analyze_schedule


def club(number: int) -> ScheduleTeam:
    return ScheduleTeam(
        provider="synthetic",
        provider_team_id=str(number),
        abbreviation=f"AA{chr(64 + number)}",
        name=None,
    )


def game(key: str, instant: str, **changes: object) -> ScheduledGame:
    data: dict[str, object] = dict(
        provider_game_id=key,
        season="20262027",
        game_type=GameType.REGULAR,
        game_type_code="2",
        home=club(1),
        away=club(2),
        reported_date=date(2026, 11, 1),
        start_time_utc=datetime.fromisoformat(instant),
        state=GameState.SCHEDULED,
        state_code="FUT",
        schedule_state_code="OK",
        schedule_normal=True,
    )
    data.update(changes)
    return ScheduledGame.model_validate(data)


def snapshot(*games: ScheduledGame, **changes: object) -> ScheduleSnapshot:
    data: dict[str, object] = dict(
        season="20262027",
        teams=(club(1), club(2), club(3)),
        games=games,
        covered_dates=frozenset(
            date(2026, 10, 29) + timedelta(days=i) for i in range(8)
        ),
        cohort_verified=True,
        coverage_contract_verified=True,
        issues=(),
        observed_at_utc=datetime(2026, 10, 1, tzinfo=UTC),
        coverage_timezone="America/Toronto",
    )
    data.update(changes)
    return ScheduleSnapshot.model_validate(data)


def test_counts_opponents_idle_team_and_ranking() -> None:
    report = analyze_schedule(
        snapshot(game("one", "2026-11-01T23:00:00Z")),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert report.ranking_available
    assert [(s.team.abbreviation, s.total) for s in report.summaries] == [
        ("AAA", 1),
        ("AAB", 1),
        ("AAC", 0),
    ]
    assert report.most_games == ("AAA", "AAB")
    assert report.fewest_games == ("AAC",)
    assert report.summaries[0].games[0].away.abbreviation == "AAB"


def test_local_midnight_filter_and_b2b_context() -> None:
    report = analyze_schedule(
        snapshot(
            game("before", "2026-11-01T01:00:00Z"),
            game("inside", "2026-11-01T23:00:00Z"),
        ),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("America/Toronto"),
    )
    summary = report.summaries[0]
    assert summary.total == 1
    assert [g.provider_game_id for g in summary.games] == ["inside"]
    assert summary.back_to_back_pairs == (("before", "inside"),)


def test_dst_repeated_hour_is_not_two_days() -> None:
    report = analyze_schedule(
        snapshot(
            game("early", "2026-11-01T05:30:00Z"), game("late", "2026-11-01T06:30:00Z")
        ),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert report.summaries[0].total == 2
    assert report.summaries[0].back_to_back_pairs == ()


@pytest.mark.parametrize(
    "changes",
    [
        {"cohort_verified": False},
        {"coverage_contract_verified": False},
        {"covered_dates": frozenset()},
        {"issues": ("INVALID_RESPONSE",)},
    ],
)
def test_incomplete_snapshot_never_ranks(changes: dict[str, object]) -> None:
    report = analyze_schedule(
        snapshot(game("one", "2026-11-01T23:00:00Z"), **changes),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("UTC"),
    )
    assert not report.ranking_available
    assert report.most_games == report.fewest_games == ()
    assert not report.summaries[2].count_complete


@pytest.mark.parametrize(
    "changes",
    [
        {"state": GameState.UNKNOWN, "state_code": "UNFAMILIAR"},
        {"state": GameState.POSTPONED, "schedule_normal": False},
        {"state": GameState.CANCELLED, "schedule_normal": False},
        {"schedule_normal": False, "schedule_state_code": "UNFAMILIAR"},
        {"game_type": GameType.UNKNOWN, "game_type_code": "99"},
        {"start_time_utc": None},
    ],
)
def test_uncertain_and_exceptional_games_never_become_normal_counts(
    changes: dict[str, object],
) -> None:
    report = analyze_schedule(
        snapshot(game("one", "2026-11-01T23:00:00Z", **changes)),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("UTC"),
    )
    assert not report.ranking_available
    assert report.summaries[0].total == 0
    assert report.summaries[0].uncertain_dated + report.summaries[0].unplaced == 1


def test_missing_context_only_does_not_block_window_counts() -> None:
    report = analyze_schedule(
        snapshot(
            game("one", "2026-11-01T23:00:00Z"),
            coverage_timezone="UTC",
            covered_dates=frozenset({date(2026, 11, 1)}),
        ),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("UTC"),
    )
    assert report.ranking_available
    assert not report.summaries[0].back_to_back_complete


def test_excluded_type_and_identical_duplicates_do_not_inflate_counts() -> None:
    regular = game("one", "2026-11-01T23:00:00Z")
    playoff = game("two", "2026-11-01T23:00:00Z", game_type=GameType.POSTSEASON)
    report = analyze_schedule(
        snapshot(regular, regular, playoff),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("UTC"),
    )
    assert report.summaries[0].total == 1


def test_conflicting_ids_and_invalid_model_identity_fail_safely() -> None:
    with pytest.raises(ValidationError):
        snapshot(
            game("one", "2026-11-01T23:00:00Z"), game("one", "2026-11-02T23:00:00Z")
        )
    with pytest.raises(ValidationError):
        game("one", "2026-11-01T23:00:00", home=club(2))


def test_coverage_cannot_be_reused_in_another_display_zone() -> None:
    report = analyze_schedule(
        snapshot(),
        start=date(2026, 11, 1),
        end=date(2026, 11, 1),
        timezone=ZoneInfo("Pacific/Auckland"),
    )
    assert not report.ranking_available


@pytest.mark.parametrize(
    "start,end",
    [(date(2026, 11, 2), date(2026, 11, 1)), (date(2026, 1, 1), date(2026, 2, 2))],
)
def test_invalid_windows_rejected(start: date, end: date) -> None:
    with pytest.raises(ValueError, match="INPUT_ERROR"):
        analyze_schedule(snapshot(), start=start, end=end, timezone=ZoneInfo("UTC"))
