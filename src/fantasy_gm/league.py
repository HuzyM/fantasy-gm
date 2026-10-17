"""Human-only private league/configuration/roster view. No AI or persistence."""

import logging
import os
import sys
import warnings
from collections.abc import Callable

import httpx

from fantasy_gm.auth import _read_hidden_input
from fantasy_gm.domain.league import League
from fantasy_gm.domain.roster import Roster
from fantasy_gm.domain.settings import LeagueSettings
from fantasy_gm.domain.team import Team
from fantasy_gm.providers.yahoo.contract_verifier import SelectionCancelled
from fantasy_gm.providers.yahoo.fantasy import (
    YahooFantasyClient,
    YahooRosterUnsupportedError,
)
from fantasy_gm.verify_nhl import _authorize, _choose, _private_terminal, _show


class _NoAvailableSelection(Exception):
    """The validated discovery/ownership result has no selectable entry."""


def _field(label: str, value: object) -> str:
    shown = ascii(str(value)) if value is not None else "not supplied / unknown"
    return f"{label}: {shown}"


def _next() -> None:
    if _read_hidden_input("Type NEXT to continue, or CANCEL: ") != "NEXT":
        raise SelectionCancelled()


def _configuration(settings: LeagueSettings) -> tuple[str, ...]:
    lines = [
        "Reported league configuration. No points or matchup results are calculated.",
        _field("Multiweek championship", settings.multiweek_championship),
        _field("Extra weekly median matchup", settings.median_matchup),
    ]
    if settings.scoring is None:
        lines.append(
            "Scoring configuration unavailable: unsupported or incomplete contract."
        )
    else:
        scoring = settings.scoring
        if scoring.incomplete:
            lines.append(
                "Partial scoring observations. Complete interpretation is unavailable; "
                "these fields are not calculation-ready."
            )
        lines.extend(
            (
                _field("Reported format code (untranslated)", scoring.format_code),
                _field("Fractional points", scoring.fractional_points),
                _field("Negative points", scoring.negative_points),
                "Modifier literals preserve reported text. Missing is never zero.",
                "Flags and position scopes remain explicit; format is not translated.",
            )
        )
        for rule in scoring.rules:
            if rule.incomplete:
                lines.append("This statistic has unresolved optional fields.")
            lines.append(
                " | ".join(
                    (
                        _field("Stat ID", rule.stat_id),
                        _field("Stat", rule.name),
                        _field("Modifier literal", rule.modifier_literal),
                        _field("Enabled", rule.enabled),
                        _field("Display only", rule.display_only),
                        _field("Hidden from display", rule.excluded_from_display),
                        _field("Position scope", rule.position_type),
                    )
                )
            )
            if rule.scopes is None:
                lines.append("Additional position scopes: not supplied / unknown")
            for scope in rule.scopes or ():
                lines.append(
                    _field("Position scope", scope.position_type)
                    + " | "
                    + _field("Display only", scope.display_only)
                )
    if settings.roster_slots is None:
        lines.append(
            "League roster slots unavailable: unsupported or incomplete contract."
        )
    else:
        if settings.roster_slots_incomplete:
            lines.append(
                "Partial roster-slot observations. "
                "Full slot configuration is UNVERIFIED."
            )
        for slot in settings.roster_slots:
            lines.append(
                _field("Slot", slot.position)
                + " | "
                + _field("Capacity", slot.capacity)
                + " | "
                + _field("Type", slot.position_type)
            )
    return tuple(lines)


def _roster(roster: Roster) -> tuple[str, ...]:
    lines = [
        "Reported roster only.",
        "Completeness, lineup legality and capacity are UNVERIFIED.",
        "Returned count does not prove reserve inclusion or completeness.",
        _field("Team", roster.team.name),
        _field("Team identity", roster.team.provider_team_id),
        _field("Reported coverage type", roster.coverage.kind),
        _field("Reported date", roster.coverage.date),
        _field("Reported week", roster.coverage.week),
        _field("Returned count", roster.returned_count),
    ]
    if roster.context_unverified:
        lines.append(
            "Some roster metadata or optional fields are unresolved. "
            "Effective coverage and completeness remain UNVERIFIED."
        )
    if not roster.entries:
        lines.append(
            "No players returned. This does not verify an empty complete roster."
        )
    for entry in roster.entries:
        lines.append(
            " | ".join(
                (
                    _field("Player", entry.name),
                    _field("Identity", entry.provider_player_id),
                    _field("Eligible", entry.eligible_positions),
                    _field("Selected", entry.selected_position),
                    _field("Flex", entry.selected_is_flex),
                )
            )
        )
        if entry.selected_coverage is None:
            lines.append("Selected-position coverage: not supplied / unknown")
        else:
            lines.extend(
                (
                    _field("Selected coverage", entry.selected_coverage.kind),
                    _field("Selected date", entry.selected_coverage.date),
                    _field("Selected week", entry.selected_coverage.week),
                )
            )
    return tuple(lines)


def _select_league(
    leagues: list[League], *, read_input: Callable[[str], str] | None = None
) -> League:
    if any(league.sport != "nhl" for league in leagues) or len(
        {league.provider_league_id for league in leagues}
    ) != len(leagues):
        raise ValueError()
    if not leagues:
        _show(("No current NHL leagues returned. Nothing was saved.",))
        if read_input is None:
            _next()
        else:
            while True:
                action = read_input("Type NEXT to finish, or CANCEL: ").upper()
                if action == "CANCEL":
                    raise SelectionCancelled()
                if action == "NEXT":
                    break
                print("No league is available. Type NEXT to finish, or CANCEL.")
        raise _NoAvailableSelection()
    options = tuple(
        _field("League", league.name)
        + " | "
        + _field("Identity", league.provider_league_id)
        for league in leagues
    )
    if read_input is None:
        index = _choose("Select your personal NHL league", options)
    else:
        index = _choose(
            "Select your personal NHL league", options, read_input=read_input
        )
    if index is None or not 0 <= index < len(leagues):
        raise SelectionCancelled()
    return leagues[index]


def _run_private() -> bool:
    print(
        "Personal read-only Yahoo session. Close AI/remote terminal views and disable "
        "recording, transcripts and screen sharing. Recording cannot be detected "
        "or undone. This approves one OAuth exchange and at most five Fantasy "
        "GETs, with no refresh or retries."
    )
    if (
        _read_hidden_input(
            "Type APPROVE PRIVATE READ-ONLY to attest and approve, or CANCEL: "
        )
        != "APPROVE PRIVATE READ-ONLY"
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
        settings: LeagueSettings | None = None

        def choose_team(owned: tuple[Team, ...]) -> str:
            nonlocal settings
            if not owned:
                _show(("No owned team returned for this league. No roster requested.",))
                _next()
                raise _NoAvailableSelection()
            index = _choose(
                "Select your owned team",
                tuple(
                    _field("Team", team.name)
                    + " | "
                    + _field("Identity", team.provider_team_id)
                    for team in owned
                ),
            )
            if index is None or not 0 <= index < len(owned):
                raise SelectionCancelled()
            settings = provider.get_league_settings(token, league.provider_league_id)
            _show(
                (_field("League", league.name), _field("Owned team", owned[index].name))
                + _configuration(settings)
            )
            _next()
            return owned[index].provider_team_id

        try:
            roster = provider.get_owned_team_roster(
                token, league_key=league.provider_league_id, choose_team=choose_team
            )
        except YahooRosterUnsupportedError:
            _show(
                (
                    "Roster unavailable: unsupported contract.",
                    "Selected league and team identities were validated.",
                    "The existing private verifier can inspect the mismatch",
                    "during a separately approved human-operated session.",
                )
            )
            _next()
            return False
        _show(_roster(roster))
        _next()
        return (
            settings is not None
            and settings.scoring is not None
            and not settings.scoring.incomplete
            and settings.roster_slots is not None
            and not settings.roster_slots_incomplete
            and not roster.context_unverified
        )


def main() -> int:
    if sys.argv[1:] == ["--help"]:
        print(
            "Usage: python -B -m fantasy_gm.league --interactive\n"
            "Human-only private league/configuration/roster view. Read-only.\n"
            "No data is saved.\n"
            "Use outside AI-observed terminals after separate approval."
        )
        return 0
    previous = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    outcome = "FAILED"
    try:
        if sys.argv[1:] != ["--interactive"]:
            raise ValueError()
        with warnings.catch_warnings(), _private_terminal():
            warnings.simplefilter("error")
            outcome = "FINISHED" if _run_private() else "PARTIAL"
    except (KeyboardInterrupt, SelectionCancelled):
        outcome = "CANCELLED"
    except _NoAvailableSelection:
        outcome = "PARTIAL"
    except Exception:
        outcome = "FAILED"  # Includes private-terminal cleanup failures.
    finally:
        logging.disable(previous)
    print(f"PRIVATE_SESSION {outcome}")
    return 0 if outcome == "FINISHED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
