"""Explicit display whitelist and pure domain schedule adapter."""

from datetime import UTC, date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fantasy_gm.domain.league import League
from fantasy_gm.domain.roster import Roster
from fantasy_gm.domain.schedule import (
    GameState,
    GameType,
    ScheduledGame,
    ScheduleSnapshot,
    ScheduleTeam,
)
from fantasy_gm.sports.nhl.roster_schedule import roster_schedule_rows
from fantasy_gm.sports.nhl.schedule import analyze_schedule

START = date(2026, 10, 19)
END = START + timedelta(days=6)
TIMEZONE = ZoneInfo("America/Toronto")


def schedule_view(snapshot: ScheduleSnapshot, start: date, end: date) -> dict[str, Any]:
    report = analyze_schedule(snapshot, start=start, end=end, timezone=TIMEZONE)
    days = []
    for offset in range((end - start).days + 1):
        day = start + timedelta(days=offset)
        daily = analyze_schedule(snapshot, start=day, end=day, timezone=TIMEZONE)
        games = {g.provider_game_id: g for s in daily.summaries for g in s.games}
        complete = bool(daily.summaries) and all(
            s.count_complete for s in daily.summaries
        )
        count: dict[str, Any] = {"state": "verified", "value": len(games)}
        if not complete:
            count = {
                "state": "incomplete" if games else "unknown",
                "reason": "Provider coverage is unverified; observed games only.",
            }
            if games:
                count["value"] = len(games)
        days.append(
            {
                "date": day.isoformat(),
                "count": count,
                "games": [
                    {
                        "id": game.provider_game_id,
                        "away": game.away.abbreviation,
                        "home": game.home.abbreviation,
                        "time": game.start_time_utc.isoformat()
                        if game.start_time_utc is not None
                        else None,
                        "state": game.state.value,
                        "upcomingEligible": (
                            game.schedule_normal
                            and game.state == GameState.SCHEDULED
                            and game.game_type == GameType.REGULAR
                            and game.start_time_utc is not None
                        ),
                    }
                    for game in games.values()
                ],
            }
        )
    return {
        "start": start.isoformat(),
        "end": end.isoformat(),
        "timezone": TIMEZONE.key,
        "observedAt": snapshot.observed_at_utc.isoformat(),
        "issues": list(snapshot.issues),
        "days": days,
        "teams": [
            {
                "code": summary.team.abbreviation,
                "observedGames": summary.total,
                "countComplete": summary.count_complete,
                "backToBackComplete": summary.back_to_back_complete,
                "uncertainDated": summary.uncertain_dated,
                "unplaced": summary.unplaced,
                "backToBackPairs": [list(pair) for pair in summary.back_to_back_pairs],
            }
            for summary in report.summaries
        ],
    }


def private_view(
    league: League,
    roster: Roster,
    snapshot: ScheduleSnapshot | None = None,
    *,
    start: date = START,
    end: date = END,
) -> dict[str, Any]:
    statuses = {}
    if snapshot is not None:
        statuses = {
            row.player.provider_player_id: row.status
            for row in roster_schedule_rows(
                roster,
                snapshot,
                roster_season=league.season,
                start=start,
                end=end,
                timezone=TIMEZONE,
            )
        }
    return {
        "mode": "private",
        "source": "yahoo",
        "provenance": [
            "Yahoo Fantasy Sports — data provided by Yahoo. Personal read-only use.",
            "Reported roster: completeness, coverage and lineup legality unverified.",
            "Team schedule observations do not guarantee player appearances.",
        ],
        "league": {"name": league.name, "season": league.season},
        "roster": {
            "teamName": roster.team.name,
            "returnedCount": roster.returned_count,
            "contextUnverified": roster.context_unverified,
            "coverage": {
                "kind": roster.coverage.kind,
                "date": roster.coverage.date.isoformat()
                if roster.coverage.date
                else None,
                "week": roster.coverage.week,
            },
            "entries": [
                {
                    "id": entry.provider_player_id,
                    "name": entry.name,
                    "positions": list(entry.eligible_positions)
                    if entry.eligible_positions is not None
                    else None,
                    "slot": entry.selected_position,
                    "team": entry.professional_team_code,
                    "affiliationUnverified": entry.professional_team_unverified,
                    "scheduleStatus": statuses.get(
                        entry.provider_player_id, "UNAVAILABLE"
                    ),
                }
                for entry in roster.entries
            ],
        },
        "settings": None,
        "planningWindow": {
            "start": start.isoformat(),
            "end": end.isoformat(),
            "timezone": TIMEZONE.key,
        },
        "schedule": schedule_view(snapshot, start, end) if snapshot else None,
    }


def synthetic_view() -> dict[str, Any]:
    home, away = (
        ScheduleTeam(provider="synthetic", provider_team_id=code, abbreviation=code)
        for code in ("TOR", "EDM")
    )
    snapshot = ScheduleSnapshot(
        season="20262027",
        teams=(home, away),
        games=tuple(
            ScheduledGame(
                provider_game_id=f"synthetic-{offset}",
                season="20262027",
                game_type=GameType.REGULAR,
                game_type_code="synthetic",
                home=home,
                away=away,
                reported_date=START + timedelta(days=offset),
                start_time_utc=datetime(2026, 10, 19 + offset, 23, tzinfo=UTC),
                state=GameState.SCHEDULED,
                state_code=None,
                schedule_state_code=None,
                schedule_normal=True,
            )
            for offset in (0, 2, 3)
        ),
        covered_dates=frozenset(),
        coverage_timezone=TIMEZONE.key,
        cohort_verified=False,
        coverage_contract_verified=False,
        issues=("SYNTHETIC_EXAMPLE",),
        observed_at_utc=datetime(2026, 10, 18, tzinfo=UTC),
    )
    return {
        "mode": "synthetic",
        "source": "synthetic",
        "provenance": ["Synthetic example only. No live Yahoo or NHL observations."],
        "league": None,
        "roster": None,
        "settings": None,
        "schedule": schedule_view(snapshot, START, END),
    }
