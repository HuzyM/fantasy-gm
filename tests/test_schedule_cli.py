"""Human-facing synthetic demo, never a claim of live NHL availability."""

import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

import fantasy_gm.schedule as schedule_cli
from fantasy_gm.domain.schedule import (
    GameState,
    GameType,
    ScheduledGame,
    ScheduleSnapshot,
    ScheduleTeam,
)
from fantasy_gm.schedule import main


def test_synthetic_demo_counts_opponents_daily_and_b2b(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "--demo",
                "--season",
                "20262027",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-07",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "SYNTHETIC DEMO" in output
    assert "America/Toronto" in output
    assert "AAA" in output and "ABF" in output
    assert "Most games" in output and "Fewest games" in output
    assert "HOME" in output and "AWAY" in output
    assert "B2B" in output
    assert "2026-11-01" in output and "2026-11-07" in output
    assert "reschedule history unavailable" in output


def test_live_flag_cannot_enable_access(capsys: pytest.CaptureFixture[str]) -> None:
    assert (
        main(
            [
                "--live",
                "--season",
                "20262027",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-07",
            ]
        )
        == 2
    )
    assert "ACCESS_NOT_ENABLED" in capsys.readouterr().err


@pytest.mark.parametrize(
    "args",
    [
        [],
        ["--demo", "--season", "wrong", "--from", "2026-11-01", "--to", "2026-11-07"],
        [
            "--demo",
            "--season",
            "20262027",
            "--from",
            "2026-11-07",
            "--to",
            "2026-11-01",
        ],
        [
            "--demo",
            "--season",
            "20262027",
            "--from",
            "2026-11-01",
            "--to",
            "2026-11-07",
            "--timezone",
            "Missing/Zone",
        ],
    ],
)
def test_invalid_cli_inputs_do_not_send(
    args: list[str], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main(args) == 2
    assert not capsys.readouterr().out


def test_standalone_import_has_no_yahoo_dependency() -> None:
    program = (
        "import sys; import fantasy_gm.schedule; "
        "assert not any(n.startswith('fantasy_gm.providers.yahoo') "
        "or n == 'fantasy_gm.verify_nhl' for n in sys.modules)"
    )
    result = subprocess.run(
        [sys.executable, "-c", program],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_help_is_safe(capsys: pytest.CaptureFixture[str]) -> None:
    assert main(["--help"]) == 0
    assert "--demo" in capsys.readouterr().out


def _presentation_snapshot(instants: tuple[str, ...]) -> ScheduleSnapshot:
    teams = tuple(
        ScheduleTeam(provider="synthetic", provider_team_id=str(i), abbreviation=code)
        for i, code in enumerate(("AAA", "AAB"), 1)
    )
    games = tuple(
        ScheduledGame(
            provider_game_id=str(i),
            season="20262027",
            game_type=GameType.REGULAR,
            game_type_code="2",
            home=teams[0],
            away=teams[1],
            reported_date=datetime.fromisoformat(instant).date(),
            start_time_utc=datetime.fromisoformat(instant),
            state=GameState.SCHEDULED,
            state_code="FUT",
            schedule_state_code="OK",
            schedule_normal=True,
        )
        for i, instant in enumerate(instants, 1)
    )
    return ScheduleSnapshot(
        season="20262027",
        teams=teams,
        games=games,
        covered_dates=frozenset(
            date(2026, 10, 28) + timedelta(days=i) for i in range(12)
        ),
        coverage_timezone="America/Toronto",
        cohort_verified=True,
        coverage_contract_verified=True,
        issues=(),
        observed_at_utc=datetime(2026, 10, 16, tzinfo=UTC),
    )


def _use_presentation_snapshot(
    monkeypatch: pytest.MonkeyPatch, instants: tuple[str, ...]
) -> None:
    def demo(
        season: str, start: date, end: date, timezone: ZoneInfo
    ) -> ScheduleSnapshot:
        return _presentation_snapshot(instants)

    monkeypatch.setattr(schedule_cli, "_demo", demo)


def test_b2b_pairs_are_grouped_and_shared_games_are_shown_once(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _use_presentation_snapshot(
        monkeypatch,
        (
            "2026-11-01T23:00:00Z",
            "2026-11-02T23:00:00Z",
            "2026-11-03T23:00:00Z",
        ),
    )
    assert (
        main(
            [
                "--demo",
                "--season",
                "20262027",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-03",
                "--view",
                "back-to-backs",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    team_output = output.split("AAA B2B", 1)[1].split("AAB B2B", 1)[0]
    assert "Pair 1: 2026-11-01 -> 2026-11-02" in team_output
    assert "Pair 2: 2026-11-02 -> 2026-11-03" in team_output
    assert team_output.count("ID 2") == 1
    assert "Game 2: shown above (2026-11-02)" in team_output
    assert "outside requested window" not in output
    assert "may include outside-window context" not in output


@pytest.mark.parametrize(
    "start,end,outside,in_window",
    [
        ("2026-11-01", "2026-11-01", "2026-10-31", "2026-11-01"),
        ("2026-10-31", "2026-10-31", "2026-11-01", "2026-10-31"),
    ],
)
def test_b2b_context_labels_only_the_actual_outside_local_date(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    start: str,
    end: str,
    outside: str,
    in_window: str,
) -> None:
    # The first game's UTC date is Nov 1, but its Toronto date is Oct 31.
    _use_presentation_snapshot(
        monkeypatch,
        (
            "2026-11-01T01:00:00Z",
            "2026-11-01T23:00:00Z",
        ),
    )
    assert (
        main(
            [
                "--demo",
                "--season",
                "20262027",
                "--from",
                start,
                "--to",
                end,
                "--view",
                "back-to-backs",
            ]
        )
        == 0
    )
    lines = capsys.readouterr().out.splitlines()
    tagged = [line for line in lines if "outside requested window" in line]
    assert len(tagged) == 2  # Once for each team's context game.
    assert all(outside in line for line in tagged)
    inside_lines = [line for line in lines if f"{in_window}T" in line]
    assert inside_lines
    assert all("outside requested window" not in line for line in inside_lines)


def test_all_32_team_tie_has_one_concise_ranking_message(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert (
        main(
            [
                "--demo",
                "--season",
                "20262027",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-03",
                "--view",
                "counts",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert output.count("All 32 teams are tied at 2 games each.") == 1
    assert "Most games:" not in output and "Fewest games:" not in output
    assert (
        sum("games (complete synthetic)" in line for line in output.splitlines()) == 32
    )


@pytest.mark.parametrize(
    "instants,count,unit",
    [
        ((), 0, "games"),
        (("2026-11-01T23:00:00Z",), 1, "game"),
    ],
)
def test_zero_and_one_game_ties_are_explicit(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    instants: tuple[str, ...],
    count: int,
    unit: str,
) -> None:
    _use_presentation_snapshot(monkeypatch, instants)
    assert (
        main(
            [
                "--demo",
                "--season",
                "20262027",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-01",
                "--view",
                "counts",
            ]
        )
        == 0
    )
    output = capsys.readouterr().out
    assert f"All 2 teams are tied at {count} {unit} each." in output
    assert "Most games:" not in output and "Fewest games:" not in output


def test_incomplete_equal_counts_do_not_claim_a_tie(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _use_presentation_snapshot(monkeypatch, ())
    assert (
        main(
            [
                "--demo",
                "--season",
                "20262027",
                "--from",
                "2026-11-01",
                "--to",
                "2026-11-01",
                "--view",
                "counts",
                "--timezone",
                "UTC",
            ]
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "PARTIAL" in output
    assert "teams are tied" not in output
    assert "Most games:" not in output and "Fewest games:" not in output
