"""Human-started local launcher. Never execute private mode through an agent."""

import argparse
import logging
import os
import warnings
from collections.abc import Sequence
from datetime import date, datetime, timedelta

import httpx
import uvicorn

from fantasy_gm.auth import _read_hidden_input
from fantasy_gm.domain.league import League
from fantasy_gm.domain.roster import Roster
from fantasy_gm.domain.schedule import ScheduleSnapshot
from fantasy_gm.domain.team import Team
from fantasy_gm.league import _field, _select_league
from fantasy_gm.providers.yahoo.contract_verifier import SelectionCancelled
from fantasy_gm.providers.yahoo.fantasy import YahooFantasyClient
from fantasy_gm.schedule_service import ScheduleService
from fantasy_gm.verify_nhl import _authorize, _choose, _private_terminal
from fantasy_gm.web import BrowserSession, create_app
from fantasy_gm.web.data import TIMEZONE, private_view, schedule_view


def _load_private() -> tuple[League, Roster]:
    print(
        "Human-only private browser session. Close AI/browser automation, remote "
        "views, transcripts and recording before continuing. This approves one "
        "OAuth exchange and at most four Yahoo GETs: league discovery, owned teams, "
        "membership and selected roster. No refresh, retries or settings reads. "
        "The browser will receive only selected display fields. Session expires "
        "after 20 minutes. Browser extensions and recording cannot be controlled."
    )
    if _read_hidden_input("Type APPROVE PRIVATE BROWSER, or CANCEL: ") != (
        "APPROVE PRIVATE BROWSER"
    ):
        raise SelectionCancelled()
    if os.environ.get("YAHOO_AI_TOOLS_ENABLED", "false") != "false":
        raise ValueError()
    with httpx.Client(
        transport=httpx.HTTPTransport(retries=0, trust_env=False), trust_env=False
    ) as http:
        token = _authorize(http)
        provider = YahooFantasyClient(http_client=http)
        league = _select_league(provider.list_my_hockey_leagues(token))

        def choose_team(owned: tuple[Team, ...]) -> str:
            if not owned:
                raise SelectionCancelled()
            index = _choose(
                "Select your owned team",
                tuple(_field("Team", team.name) for team in owned),
            )
            if index is None or not 0 <= index < len(owned):
                raise SelectionCancelled()
            return owned[index].provider_team_id

        roster = provider.get_owned_team_roster(
            token, league_key=league.provider_league_id, choose_team=choose_team
        )
        del token, provider
    return league, roster


def _schedule_start(now: datetime) -> date:
    return now.astimezone(TIMEZONE).date()


def _load_public_schedule() -> tuple[ScheduleSnapshot, date, date]:
    print(
        "Public NHL schedule only: one startup load, at most two PuckAPI requests "
        "(normally six credits), no retries or browser refresh requests. "
        "No Yahoo identities are supplied to PuckAPI."
    )
    if _read_hidden_input("Type APPROVE PUBLIC SCHEDULE, or CANCEL: ") != (
        "APPROVE PUBLIC SCHEDULE"
    ):
        raise SelectionCancelled()
    start = _schedule_start(datetime.now(TIMEZONE))
    end = start + timedelta(days=6)
    year = start.year if start.month >= 7 else start.year - 1
    with ScheduleService() as service:
        _, snapshot = service.get_schedule(
            season=f"{year}{year + 1}", start=start, end=end, timezone=TIMEZONE
        )
    return snapshot, start, end


def _serve(args: argparse.Namespace, session: BrowserSession) -> None:
    url = f"http://127.0.0.1:{args.port}/"
    if session.private:
        url += "#access=" + session.capability
    print("Open in your browser: " + url)
    print("Keep this process open. Ctrl+C stops it and discards the session.")
    uvicorn.run(
        create_app(port=args.port, session=session),
        host="127.0.0.1",
        port=args.port,
        access_log=False,
        log_config=None,
        log_level="critical",
        server_header=False,
        proxy_headers=False,
        workers=1,
        timeout_keep_alive=5,
        limit_concurrency=32,
        ws="none",
    )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Local Fantasy GM browser application")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--private", action="store_true")
    parser.add_argument("--interactive", action="store_true")
    parser.add_argument("--public-schedule", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as error:
        return int(error.code or 0)
    if not 1024 <= args.port <= 65535:
        print("Use a port from 1024 through 65535.")
        return 2
    if (args.private or args.public_schedule) and not args.interactive:
        print("Provider startup loads require --interactive in a human terminal.")
        return 2
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    session = BrowserSession(private=args.private)
    try:
        if args.private or args.public_schedule:
            with warnings.catch_warnings(), _private_terminal():
                warnings.simplefilter("error")
                if args.private:
                    league, roster = _load_private()
                if args.public_schedule:
                    snapshot, start, end = _load_public_schedule()
                    if args.private:
                        session.load(
                            private_view(league, roster, snapshot, start=start, end=end)
                        )
                    else:
                        session.view = {
                            "mode": "synthetic",
                            "source": "puckapi",
                            "provenance": [
                                "Public PuckAPI schedule observation; no Yahoo roster.",
                                "Coverage may be incomplete; appearances unverified.",
                            ],
                            "league": None,
                            "roster": None,
                            "settings": None,
                            "schedule": schedule_view(snapshot, start, end),
                        }
                        session.schedule = "observed"
                    del snapshot
                elif args.private:
                    session.load(private_view(league, roster))
                if args.private:
                    del league, roster
                _serve(args, session)
        else:
            _serve(args, session)
    except (Exception, KeyboardInterrupt):
        print("Local session ended or could not start. Nothing was saved.")
        return 1
    finally:
        session.clear()
        logging.disable(previous)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
