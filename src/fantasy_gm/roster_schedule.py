"""Human-only roster schedule session. No AI interface or persistent data."""

import argparse
import logging
import math
import os
import warnings
from collections.abc import Sequence
from datetime import date
from zoneinfo import ZoneInfo

import httpx

from fantasy_gm.auth import _read_visible_input
from fantasy_gm.domain.roster import Roster
from fantasy_gm.domain.schedule import ScheduleSnapshot, TeamScheduleSummary
from fantasy_gm.domain.team import Team
from fantasy_gm.league import _field, _select_league
from fantasy_gm.providers.puckapi import PuckApiError
from fantasy_gm.providers.yahoo.contract_verifier import SelectionCancelled
from fantasy_gm.providers.yahoo.fantasy import YahooFantasyClient
from fantasy_gm.schedule import _game_line, _input_date
from fantasy_gm.schedule_service import ScheduleService
from fantasy_gm.sports.nhl.roster_schedule import PlayerSchedule, roster_schedule_rows
from fantasy_gm.sports.nhl.schedule import analyze_schedule, validate_window
from fantasy_gm.verify_nhl import _authorize, _BackRequested, _private_terminal
from fantasy_gm.verify_nhl import _choose as _private_choose
from fantasy_gm.verify_nhl import _show as _private_show


def _show(lines: tuple[str, ...]) -> None:
    _private_show(lines, read_input=_read_visible_input, allow_back=True)


def _choose(
    title: str, options: tuple[str, ...], *, allow_back: bool = True
) -> int | None:
    return _private_choose(
        title, options, read_input=_read_visible_input, allow_back=allow_back
    )


def _confirm_action(expected: str, prompt: str, *, allow_back: bool = True) -> None:
    while True:
        action = _read_visible_input(prompt)
        if action.upper() == "CANCEL":
            raise SelectionCancelled()
        if action.upper() == "BACK" and allow_back:
            raise _BackRequested()
        if action == expected:
            return
        print(f"Invalid confirmation. Type {expected} exactly, or CANCEL.")


def _next() -> None:
    _confirm_action("NEXT", "Type NEXT, BACK to the menu, or CANCEL: ")


def _window(year: int) -> tuple[date, date]:
    while True:
        first = _read_visible_input("Start date YYYY-MM-DD, BACK, or CANCEL: ")
        if first.upper() == "CANCEL":
            raise SelectionCancelled()
        if first.upper() == "BACK":
            raise _BackRequested()
        try:
            start = _input_date(first)
            if not year <= start.year <= year + 1:
                raise ValueError()
        except ValueError:
            print(f"Invalid start date. Use YYYY-MM-DD in {year} or {year + 1}.")
            continue
        while True:
            last = _read_visible_input("End date YYYY-MM-DD, BACK, or CANCEL: ")
            if last.upper() == "CANCEL":
                raise SelectionCancelled()
            if last.upper() == "BACK":
                break
            try:
                end = _input_date(last)
                validate_window(start, end)
                if not year <= start.year <= end.year <= year + 1:
                    raise ValueError()
            except ValueError:
                print(
                    "Invalid end date. Use an inclusive 1-31-day window in the season."
                )
                continue
            return start, end


def _player_line(row: PlayerSchedule) -> str:
    line = (
        _field("Player", row.player.name)
        + " | "
        + _field("Yahoo identity", row.player.provider_player_id)
        + " | "
        + _field("Reported NHL team", row.player.professional_team_code)
        + " | "
        + row.status
    )
    if row.summary is not None:
        line += (
            f" | {row.summary.total} observed team games (total unknown)"
            f" | uncertain={row.summary.uncertain_dated}"
            f" unplaced={row.summary.unplaced}"
        )
    return line


def _team_lines(
    summary: TeamScheduleSummary,
    snapshot: ScheduleSnapshot,
    start: date,
    end: date,
    timezone: ZoneInfo,
) -> tuple[str, ...]:
    lines = [
        _field("NHL team", summary.team.abbreviation),
        f"{summary.total} observed games; total and complete B2B coverage unknown.",
        f"Uncertain dated games={summary.uncertain_dated}; unplaced={summary.unplaced}",
    ]
    for game in summary.games:
        side = "HOME" if game.home == summary.team else "AWAY"
        lines.append(side + " | " + _game_line(game, timezone))
    by_id = {g.provider_game_id: g for g in snapshot.games}
    for first, second in summary.back_to_back_pairs:
        dates = tuple(by_id[key].start_time_utc for key in (first, second))
        local = tuple(t.astimezone(timezone).date() for t in dates if t is not None)
        context = (
            " (includes outside-window context)"
            if any(not start <= d <= end for d in local)
            else ""
        )
        lines.append(f"Observed B2B: {local[0]} -> {local[1]}" + context)
    if not summary.back_to_back_pairs:
        lines.append("No B2B observed; this does not prove none are scheduled.")
    for game in snapshot.games:
        if game.start_time_utc is None and summary.team in (game.home, game.away):
            lines.append("Unplaced | " + _game_line(game, timezone))
    return tuple(lines)


def _view(
    service: ScheduleService,
    roster: Roster,
    year: int,
    start: date,
    end: date,
    timezone: ZoneInfo,
    *,
    player: int | None = None,
    team_query: bool = False,
    refresh: bool = False,
) -> None:
    try:
        cache_status, snapshot = service.get_schedule(
            season=f"{year}{year + 1}",
            start=start,
            end=end,
            timezone=timezone,
            refresh=refresh,
        )
    except PuckApiError as error:
        _show(
            (
                "Schedule unavailable: " + error.code,
                "No expired observation substituted.",
            )
        )
        _next()
        return
    header = (
        cache_status,
        f"Window {start} through {end} | {timezone.key}",
        "PuckAPI observation: " + snapshot.observed_at_utc.isoformat(),
        "Team schedule observations, not guaranteed player appearances.",
        "Yahoo-reported affiliation may change; roster completeness is unverified.",
    ) + snapshot.issues
    if team_query:
        report = analyze_schedule(snapshot, start=start, end=end, timezone=timezone)
        if not report.summaries:
            _show(header + ("No supported NHL teams available.",))
        else:
            index = _choose(
                "Select NHL team (no Yahoo request)",
                tuple(s.team.abbreviation for s in report.summaries),
            )
            if index is None:
                return
            _show(
                header
                + _team_lines(report.summaries[index], snapshot, start, end, timezone)
            )
    else:
        rows = roster_schedule_rows(
            roster,
            snapshot,
            roster_season=year,
            start=start,
            end=end,
            timezone=timezone,
        )
        if player is None:
            _show(
                header
                + tuple(_player_line(row) for row in rows)
                + ("Select a player for opponents, home/away games and B2B dates.",)
            )
        else:
            row = rows[player]
            details = (
                _team_lines(row.summary, snapshot, start, end, timezone)
                if row.summary is not None
                else (
                    "No supported affiliation join; use the independent NHL team view.",
                )
            )
            _show(header + (_player_line(row),) + details)
    _next()


def _run_private(ttl_seconds: float) -> None:
    print(
        "Private human-only Yahoo roster and PuckAPI schedule session. Close AI/remote "
        "views and disable recording/transcripts. This approves one OAuth exchange "
        "and at most four Yahoo GETs, no Yahoo refresh or retries. Each schedule "
        "cache miss or explicit refresh makes at most two PuckAPI requests, normally "
        "six credits. No data is saved or sent to an AI client."
    )
    _confirm_action(
        "APPROVE PRIVATE READ-ONLY",
        "Type APPROVE PRIVATE READ-ONLY to attest and approve, or CANCEL: ",
        allow_back=False,
    )
    if os.environ.get("YAHOO_AI_TOOLS_ENABLED", "false") != "false":
        raise ValueError()
    with httpx.Client(
        transport=httpx.HTTPTransport(retries=0, trust_env=False), trust_env=False
    ) as http:
        token = _authorize(http)
        provider = YahooFantasyClient(http_client=http)
        league = _select_league(
            provider.list_my_hockey_leagues(token), read_input=_read_visible_input
        )
        if league.season is None or not 1000 <= league.season < 9999:
            raise ValueError()

        def choose_team(owned: tuple[Team, ...]) -> str:
            if not owned:
                raise SelectionCancelled()
            index = _choose(
                "Select your owned Yahoo team",
                tuple(_field("Team", t.name) for t in owned),
                allow_back=False,
            )
            if index is None:
                raise SelectionCancelled()
            return owned[index].provider_team_id

        roster = provider.get_owned_team_roster(
            token, league_key=league.provider_league_id, choose_team=choose_team
        )
        del token, provider
    timezone = ZoneInfo("America/Toronto")
    while True:
        try:
            start, end = _window(league.season)
            break
        except _BackRequested:
            print("No previous window. Enter dates or CANCEL; Yahoo is already loaded.")
    with ScheduleService(ttl_seconds=ttl_seconds) as service:
        try:
            _view(service, roster, league.season, start, end, timezone)
        except _BackRequested:
            pass
        while True:
            try:
                _show(
                    (
                        "1: Roster summary",
                        "2: Select roster player",
                        "3: Select NHL team",
                        "4: Change date window",
                        "5: Refresh schedule (spends credits)",
                        "6: Exit",
                    )
                )
            except _BackRequested:
                continue
            while True:
                command = _read_visible_input(
                    "Choose session command 1-6, BACK, or CANCEL: "
                ).upper()
                if command == "CANCEL":
                    raise SelectionCancelled()
                if command in ("1", "2", "3", "4", "5", "6"):
                    break
                print("Invalid selection. You are at the menu; choose 1-6 or CANCEL.")
            if command == "6":
                return
            try:
                if command == "2":
                    index = _choose(
                        "Select roster player",
                        tuple(
                            _field("Player", p.name)
                            + " | "
                            + _field("Identity", p.provider_player_id)
                            for p in roster.entries
                        ),
                    )
                    if index is None:
                        _next()
                        continue
                    _view(
                        service,
                        roster,
                        league.season,
                        start,
                        end,
                        timezone,
                        player=index,
                    )
                elif command == "3":
                    _view(
                        service,
                        roster,
                        league.season,
                        start,
                        end,
                        timezone,
                        team_query=True,
                    )
                elif command in ("1", "4", "5"):
                    if command == "4":
                        start, end = _window(league.season)
                    if command == "5":
                        _confirm_action(
                            "REFRESH",
                            "Type REFRESH to spend credits, BACK, or CANCEL: ",
                        )
                    _view(
                        service,
                        roster,
                        league.season,
                        start,
                        end,
                        timezone,
                        refresh=command == "5",
                    )
            except _BackRequested:
                continue


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Human-only roster schedule session; no persistence or AI access."
    )
    parser.add_argument("--interactive", action="store_true", required=True)
    parser.add_argument("--cache-ttl-seconds", type=float, default=3600)
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    outcome = "FAILED"
    try:
        if not math.isfinite(args.cache_ttl_seconds) or args.cache_ttl_seconds <= 0:
            raise ValueError()
        with warnings.catch_warnings(), _private_terminal():
            warnings.simplefilter("error")
            _run_private(args.cache_ttl_seconds)
            outcome = "FINISHED"
    except (KeyboardInterrupt, SelectionCancelled):
        outcome = "CANCELLED"
    except Exception:
        outcome = "FAILED"
    finally:
        logging.disable(previous)
    print("PRIVATE_SESSION " + outcome)
    return 0 if outcome == "FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
