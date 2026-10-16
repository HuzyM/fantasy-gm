"""Standalone synthetic demo and human-operated PuckAPI schedule observations."""

import argparse
import sys
from collections.abc import Sequence
from datetime import date, timedelta
from time import monotonic
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import httpx

from fantasy_gm.domain.schedule import GameType, ScheduledGame, ScheduleSnapshot
from fantasy_gm.providers.nhl.schedule import NhlScheduleClient, ScheduleError
from fantasy_gm.providers.puckapi import PuckApiError, PuckApiScheduleClient
from fantasy_gm.sports.nhl.schedule import analyze_schedule, validate_window


def _safe(value: object) -> str:
    return ascii(str(value))[1:-1]


def _input_date(value: str) -> date:
    parsed = date.fromisoformat(value)
    if parsed.isoformat() != value:
        raise ValueError("INPUT_ERROR")
    return parsed


def _demo(season: str, start: date, end: date, timezone: ZoneInfo) -> ScheduleSnapshot:
    """Invented 32-club schedule with a known synthetic UTC date profile.

    This is the only place a source date profile is qualified. The adapter's
    unqualified NHL date profile is never promoted for an actual response.
    """
    teams = [
        dict(
            id=i + 1,
            seasonId=int(season),
            abbrev=f"A{chr(65 + i // 26)}{chr(65 + i % 26)}",
            name={"default": f"Demo Club {i + 1:02d}"},
        )
        for i in range(32)
    ]

    def serve(request: httpx.Request) -> httpx.Response:
        if "schedule-calendar/" in request.url.path:
            return httpx.Response(200, json={"teams": teams})
        first = date.fromisoformat(request.url.path.rsplit("/", 1)[1])
        buckets: list[dict[str, object]] = []
        for offset in range(7):
            day = first + timedelta(days=offset)
            games: list[dict[str, object]] = []
            for pair in range(16):
                if (pair + day.day) % 3 == 0:
                    continue
                home, away = teams[2 * pair : 2 * pair + 2]
                if day.day % 2:
                    home, away = away, home
                games.append(
                    dict(
                        id=day.toordinal() * 100 + pair + 1,
                        season=int(season),
                        gameType=2,
                        homeTeam=home,
                        awayTeam=away,
                        startTimeUTC=f"{day.isoformat()}T21:00:00Z",
                        gameState="FUT",
                        gameScheduleState="OK",
                    )
                )
            buckets.append(
                dict(date=day.isoformat(), numberOfGames=len(games), games=games)
            )
        return httpx.Response(200, json={"gameWeek": buckets})

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        snapshot = client.get_schedule(
            season=season,
            start=start,
            end=end,
            timezone=timezone,
            deadline=monotonic() + 90,
        )
    if snapshot.issues:
        return snapshot
    # Generated daily 21:00Z events, fetched with two UTC dates on both sides,
    # cover every requested local date plus its context for the selected zone.
    return snapshot.model_copy(
        update={
            "cohort_verified": True,
            "coverage_contract_verified": True,
            "coverage_timezone": timezone.key,
            "covered_dates": frozenset(
                start + timedelta(days=i) for i in range(-1, (end - start).days + 2)
            ),
        }
    )


def _game_line(game: ScheduledGame, timezone: ZoneInfo) -> str:
    instant = game.start_time_utc
    when = instant.astimezone(timezone).isoformat() if instant else "time unknown"
    provenance = (
        f" | source date {game.reported_date} | UTC "
        + (instant.isoformat() if instant else "unknown")
        if game.home.provider == "puckapi"
        else ""
    )
    return (
        f"{when} | {_safe(game.away.abbreviation)} at {_safe(game.home.abbreviation)}"
        f" | {game.state.value} | codes {_safe(game.state_code)}/"
        f"{_safe(game.schedule_state_code)} | ID {_safe(game.provider_game_id)}"
        + provenance
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="NHL schedule intelligence (synthetic demo or PuckAPI REST)"
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--demo", action="store_true", help="invented games; no network")
    mode.add_argument(
        "--puckapi", action="store_true", help="live REST; requires PUCKAPI_API_KEY"
    )
    mode.add_argument(
        "--live", action="store_true", help="NHL-operated source remains disabled"
    )
    parser.add_argument("--season", required=True)
    parser.add_argument("--from", dest="start", required=True)
    parser.add_argument("--to", dest="end", required=True)
    parser.add_argument("--timezone", default="America/Toronto")
    parser.add_argument(
        "--game-type",
        choices=("regular", "preseason", "playoff", "all"),
        default="regular",
    )
    parser.add_argument(
        "--limit", type=int, default=500, help="PuckAPI result cap, 1-500"
    )
    parser.add_argument(
        "--view",
        choices=("all", "counts", "opponents", "back-to-backs", "daily"),
        default="all",
    )
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)
    try:
        start, end = _input_date(args.start), _input_date(args.end)
        validate_window(start, end)
        # Keep demo dates within the requested season's start/end years.
        if (
            len(args.season) != 8
            or not args.season.isascii()
            or not args.season.isdecimal()
            or int(args.season[4:]) != int(args.season[:4]) + 1
        ):
            raise ValueError("INPUT_ERROR")
        if not int(args.season[:4]) <= start.year <= end.year <= int(args.season[4:]):
            raise ValueError("INPUT_ERROR")
        timezone = ZoneInfo(args.timezone)
        if not 1 <= args.limit <= 500:
            raise ValueError("INPUT_ERROR")
        game_type = {
            "regular": GameType.REGULAR,
            "preseason": GameType.EXHIBITION,
            "playoff": GameType.POSTSEASON,
            "all": None,
        }[args.game_type]
        if args.live:
            raise ScheduleError("ACCESS_NOT_ENABLED")
        if args.puckapi:
            with PuckApiScheduleClient.from_env() as client:
                snapshot = client.get_schedule(
                    season=args.season,
                    start=start,
                    end=end,
                    timezone=timezone,
                    game_type=game_type,
                    limit=args.limit,
                    deadline=monotonic() + 90,
                )
        else:
            snapshot = _demo(args.season, start, end, timezone)
        report = analyze_schedule(
            snapshot,
            start=start,
            end=end,
            timezone=timezone,
            game_type=game_type,
        )
    except (ValueError, OverflowError, ZoneInfoNotFoundError):
        print("INPUT_ERROR", file=sys.stderr)
        return 2
    except (ScheduleError, PuckApiError) as error:
        print(error.code, file=sys.stderr)
        return 2
    print(
        "PuckAPI NHL schedule observation (REST; no Yahoo access)."
        if args.puckapi
        else "SYNTHETIC DEMO - invented clubs and games; no real NHL data or requests."
    )
    print(
        f"Season {_safe(snapshot.season)} | {start} through {end} | "
        f"{_safe(timezone.key)}"
    )
    print(
        f"Observed {snapshot.observed_at_utc.isoformat()} | "
        + (
            (
                "complete observed count coverage"
                if args.puckapi
                else "complete synthetic count coverage"
            )
            if report.ranking_available
            else "PARTIAL; totals unknown; rankings unavailable"
        )
    )
    print(
        "Source completeness/date cutover unverified; reschedule history unavailable."
        if args.puckapi
        else "Real NHL access disabled; reschedule history unavailable."
    )
    by_id = {g.provider_game_id: g for g in snapshot.games}
    for summary in report.summaries:
        team = summary.team
        if args.view in ("all", "counts"):
            coverage = (
                ("complete observed" if args.puckapi else "complete synthetic")
                if summary.count_complete
                else "observed; total unknown"
            )
            print(
                f"{team.abbreviation}: {summary.total} games ({coverage}); "
                f"scheduled={summary.scheduled} live={summary.in_progress} "
                f"completed={summary.completed} uncertain={summary.uncertain_dated} "
                f"unplaced={summary.unplaced}"
            )
        if args.view in ("all", "opponents"):
            for game in summary.games:
                side = "HOME" if game.home == team else "AWAY"
                print(f"{team.abbreviation} {side} | {_game_line(game, timezone)}")
        if args.view in ("all", "back-to-backs"):
            print(
                f"{team.abbreviation} B2B (consecutive dates in {_safe(timezone.key)}):"
            )
            shown_games: dict[str, int] = {}
            for pair_number, pair in enumerate(summary.back_to_back_pairs, 1):
                pair_games = tuple(by_id[key] for key in pair)
                local_dates = tuple(
                    game.start_time_utc.astimezone(timezone).date()
                    if game.start_time_utc
                    else None
                    for game in pair_games
                )
                print(f"  Pair {pair_number}: {local_dates[0]} -> {local_dates[1]}")
                for game, local_date in zip(pair_games, local_dates, strict=True):
                    key = game.provider_game_id
                    if key in shown_games:
                        print(
                            f"    Game {shown_games[key]}: shown above ({local_date})"
                        )
                        continue
                    shown_games[key] = len(shown_games) + 1
                    context = (
                        " (outside requested window)"
                        if local_date is not None and not start <= local_date <= end
                        else ""
                    )
                    print(
                        f"    Game {shown_games[key]}: {_game_line(game, timezone)}"
                        f"{context}"
                    )
            if not summary.back_to_back_pairs:
                print(
                    "  none"
                    if summary.back_to_back_complete
                    else "  none observed; completeness unknown"
                )
    if args.view in ("all", "daily"):
        print("Daily schedule:")
        shown = {g.provider_game_id: g for s in report.summaries for g in s.games}
        for game in sorted(
            shown.values(),
            key=lambda g: (
                g.start_time_utc.isoformat() if g.start_time_utc else "",
                g.provider_game_id,
            ),
        ):
            print(_game_line(game, timezone))
    if args.view in ("all", "daily", "opponents"):
        unplaced = [g for g in snapshot.games if g.start_time_utc is None]
        if unplaced:
            print("Unplaced games (local date/time unknown; may affect the window):")
            for game in unplaced:
                print(_game_line(game, timezone))
    if report.ranking_available and args.view in ("all", "counts"):
        totals = {summary.total for summary in report.summaries}
        if len(totals) == 1:
            count = next(iter(totals))
            unit = "game" if count == 1 else "games"
            print(f"All {len(report.summaries)} teams are tied at {count} {unit} each.")
        else:
            print("Most games: " + ", ".join(report.most_games))
            print("Fewest games: " + ", ".join(report.fewest_games))
    for issue in report.issues:
        print(_safe(issue))
    return 0 if report.ranking_available else 1


if __name__ == "__main__":
    raise SystemExit(main())
