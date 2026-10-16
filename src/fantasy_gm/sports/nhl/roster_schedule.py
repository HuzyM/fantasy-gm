"""Pure private roster-to-public-team join; no requests, cache or persistence."""

from dataclasses import dataclass
from datetime import date
from typing import Literal
from zoneinfo import ZoneInfo

from fantasy_gm.domain.roster import Roster, RosterEntry
from fantasy_gm.domain.schedule import GameType, ScheduleSnapshot, TeamScheduleSummary
from fantasy_gm.sports.nhl.schedule import analyze_schedule


@dataclass(frozen=True)
class PlayerSchedule:
    player: RosterEntry
    summary: TeamScheduleSummary | None
    status: Literal[
        "MATCHED",
        "MISSING_AFFILIATION",
        "AFFILIATION_UNVERIFIED",
        "UNSUPPORTED_TEAM",
        "COHORT_UNVERIFIED",
        "SEASON_MISMATCH",
    ]


def roster_schedule_rows(
    roster: Roster,
    snapshot: ScheduleSnapshot,
    *,
    roster_season: int | None,
    start: date,
    end: date,
    timezone: ZoneInfo,
    game_type: GameType | None = GameType.REGULAR,
) -> tuple[PlayerSchedule, ...]:
    report = analyze_schedule(
        snapshot, start=start, end=end, timezone=timezone, game_type=game_type
    )
    by_code = {s.team.abbreviation: s for s in report.summaries}
    same_season = (
        roster_season is not None
        and snapshot.season == f"{roster_season}{roster_season + 1}"
        and (
            roster.coverage.date is None
            or roster_season <= roster.coverage.date.year <= roster_season + 1
        )
    )
    rows: list[PlayerSchedule] = []
    for player in roster.entries:
        if player.professional_team_unverified:
            rows.append(PlayerSchedule(player, None, "AFFILIATION_UNVERIFIED"))
        elif player.professional_team_code is None:
            rows.append(PlayerSchedule(player, None, "MISSING_AFFILIATION"))
        elif not same_season:
            rows.append(PlayerSchedule(player, None, "SEASON_MISMATCH"))
        elif not snapshot.cohort_verified:
            rows.append(PlayerSchedule(player, None, "COHORT_UNVERIFIED"))
        elif player.professional_team_code not in by_code:
            rows.append(PlayerSchedule(player, None, "UNSUPPORTED_TEAM"))
        else:
            rows.append(
                PlayerSchedule(
                    player, by_code[player.professional_team_code], "MATCHED"
                )
            )
    return tuple(rows)
