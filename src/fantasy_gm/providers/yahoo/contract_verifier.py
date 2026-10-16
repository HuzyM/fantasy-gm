"""Private, ephemeral NHL contract checks; no domain feature or MCP integration.

The public GET examples establish candidate shapes, not verified NHL semantics:
https://sports.yahoo.com/developer/docs/
Only the manual CLI supplies private selection/comparison callbacks. Never call
this module from an AI tool, or retain callback arguments as recorded fixtures.
"""

import logging
import re
from collections import Counter
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from enum import StrEnum
from xml.etree import ElementTree as ET

import httpx
from pydantic import SecretStr

from fantasy_gm.domain.roster import Roster, RosterCoverage, RosterEntry
from fantasy_gm.providers.yahoo.fantasy import (
    _ROSTER_FIELDS,
    YahooFantasyError,
    YahooRosterUnsupportedError,
    _fetch_xml,
    _match_owned_teams,
    _normalize_roster,
    _one,
    _roster_envelope,
    _xml_root,
    parse_league_teams,
    parse_leagues,
    parse_my_teams,
)
from fantasy_gm.providers.yahoo.settings import (
    YahooSettingsUnsupportedError,
    _bool_field,
    _modifiers,
    _scoring_structure,
    _slots,
    _stat_rules,
    _unsupported_settings,
)
from fantasy_gm.providers.yahoo.settings import (
    _settings_identity as _parse_settings_identity,
)


class Status(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNVERIFIED = "UNVERIFIED"


class Check(StrEnum):
    PRIVATE_TERMINAL = "PRIVATE_TERMINAL"
    LIVE_APPROVAL = "LIVE_APPROVAL"
    AUTHORIZATION = "AUTHORIZATION"
    LEAGUE_DISCOVERY = "LEAGUE_DISCOVERY"
    SETTINGS_STRUCTURE = "SETTINGS_STRUCTURE"
    SCORING_STRUCTURE = "SCORING_STRUCTURE"
    MODIFIER_VALUES = "MODIFIER_VALUES"
    STAT_APPLICABILITY = "STAT_APPLICABILITY"
    ROSTER_SLOTS = "ROSTER_SLOTS"
    HUMAN_POINTS_FORMAT = "HUMAN_POINTS_FORMAT"
    HUMAN_SCORING_COMPLETE = "HUMAN_SCORING_COMPLETE"
    HUMAN_POSITION_SCOPES = "HUMAN_POSITION_SCOPES"
    HUMAN_ROSTER_SLOTS = "HUMAN_ROSTER_SLOTS"
    OWNED_TEAM_MEMBERSHIP = "OWNED_TEAM_MEMBERSHIP"
    LEAGUE_TEAMS_STRUCTURE = "LEAGUE_TEAMS_STRUCTURE"
    LEAGUE_TEAMS_COMPLETENESS = "LEAGUE_TEAMS_COMPLETENESS"
    HUMAN_LEAGUE_TEAMS_COMPLETE = "HUMAN_LEAGUE_TEAMS_COMPLETE"
    ROSTER_STRUCTURE = "ROSTER_STRUCTURE"
    ROSTER_NORMALIZATION = "ROSTER_NORMALIZATION"
    PLAYER_POSITIONS = "PLAYER_POSITIONS"
    ROSTER_SLOT_CAPACITY = "ROSTER_SLOT_CAPACITY"
    ROSTER_COVERAGE = "ROSTER_COVERAGE"
    ROSTER_RETURNED_COUNT = "ROSTER_RETURNED_COUNT"
    HUMAN_PLAYER_POSITIONS = "HUMAN_PLAYER_POSITIONS"
    HUMAN_ROSTER_COVERAGE = "HUMAN_ROSTER_COVERAGE"
    HUMAN_ROSTER_COMPLETE = "HUMAN_ROSTER_COMPLETE"
    SESSION = "SESSION"


class StopReason(StrEnum):
    UNSUPPORTED_SCORING_SETTING = "UNSUPPORTED_SCORING_SETTING"
    UNSUPPORTED_SCORING_CONTAINER = "UNSUPPORTED_SCORING_CONTAINER"
    EMPTY_SCORING_COLLECTION = "EMPTY_SCORING_COLLECTION"
    UNSUPPORTED_STAT_STRUCTURE = "UNSUPPORTED_STAT_STRUCTURE"
    UNSUPPORTED_MODIFIER_STRUCTURE = "UNSUPPORTED_MODIFIER_STRUCTURE"
    UNSUPPORTED_STRUCTURE = "UNSUPPORTED_STRUCTURE"
    VALIDATION_FAILED = "VALIDATION_FAILED"
    HUMAN_CONFIRMATION_REJECTED = "HUMAN_CONFIRMATION_REJECTED"
    HUMAN_CONFIRMATION_NOT_COMPLETED = "HUMAN_CONFIRMATION_NOT_COMPLETED"
    USER_CANCELLED = "USER_CANCELLED"
    SELECTION_NOT_COMPLETED = "SELECTION_NOT_COMPLETED"
    INTERACTION_INTERRUPTED = "INTERACTION_INTERRUPTED"
    SESSION_ERROR = "SESSION_ERROR"
    VALIDATION_INCOMPLETE = "VALIDATION_INCOMPLETE"


class SelectionCancelled(Exception):
    """An explicit private menu CANCEL; carries no user input or provider data."""


class Report:
    """The shareable boundary holds enum pairs only; never provider payloads."""

    def __init__(self) -> None:
        self._statuses = dict.fromkeys(Check, Status.UNVERIFIED)
        self.active_check = Check.SESSION
        self._stop: tuple[Check, StopReason, bool] | None = None
        self._last_stop: tuple[Check, StopReason, bool] | None = None

    def enter(self, check: Check) -> None:
        self.active_check = Check(check)

    def stop(self, check: Check, reason: StopReason, *, skipped: bool = True) -> None:
        """Keep first and most recent causes without changing check statuses."""
        if type(skipped) is not bool:
            raise ValueError("Invalid skipped classification")
        entry = (Check(check), StopReason(reason), skipped)
        if self._stop is None:
            self._stop = entry
        self._last_stop = entry

    def diagnostics(self) -> tuple[str, ...]:
        if self._stop is None:
            return ()
        check, reason, skipped = self._stop
        result: tuple[str, ...] = (
            f"STOP_CHECK {check.value}",
            f"STOP_REASON {reason.value}",
            f"DOWNSTREAM_CHECKS_SKIPPED {'YES' if skipped else 'NO'}",
        )
        if self._last_stop is not None and self._last_stop != self._stop:
            check, reason, skipped = self._last_stop
            result += (
                f"LAST_STOP_CHECK {check.value}",
                f"LAST_STOP_REASON {reason.value}",
                f"LAST_DOWNSTREAM_CHECKS_SKIPPED {'YES' if skipped else 'NO'}",
            )
        return result

    def mark(self, check: Check, status: Status) -> None:
        self._statuses[Check(check)] = Status(status)

    def lines(self) -> tuple[str, ...]:
        return tuple(f"{check.value} {self._statuses[check].value}" for check in Check)

    def passed(self, check: Check) -> bool:
        return self._statuses[check] is Status.PASS

    def failed(self) -> bool:
        return Status.FAIL in self._statuses.values()


class _Stop(Exception):
    """No diagnostic values or underlying exception messages escape a stage."""


@contextmanager
def _checking(report: Report, check: Check) -> Iterator[None]:
    report.enter(check)
    try:
        yield
    except _Stop:
        raise
    except (ValueError, YahooFantasyError):
        report.mark(check, Status.FAIL)
        report.stop(check, StopReason.VALIDATION_FAILED)
        raise _Stop() from None
    else:
        report.mark(check, Status.PASS)


def _unsupported(
    report: Report,
    check: Check,
    reason: StopReason = StopReason.UNSUPPORTED_STRUCTURE,
) -> None:
    report.mark(check, Status.UNVERIFIED)
    report.stop(check, reason)
    raise _Stop()


def _private(label: str, value: str | None) -> str:
    # ascii() escapes newlines, ANSI, bidi controls, and all non-ASCII content.
    return f"{label}={ascii(value) if value is not None else 'MISSING'}"


def _structure_name(name: str, ns: str) -> str:
    """Bound/escape untrusted names; namespace URIs may contain private URLs."""
    namespace, _, local = (
        name[1:].partition("}") if name.startswith("{") else ("", "", name)
    )
    escaped = ascii(local[:64])
    shortened = len(local) > 64 or len(escaped) > 80
    label = (
        "expected Yahoo"
        if namespace == ns
        else "other URI hidden"
        if namespace
        else "none"
    )
    return f"{escaped[:80]}{' [truncated]' if shortened else ''} [namespace: {label}]"


def _structure(
    node: ET.Element,
    *,
    parent: str,
    ns: str,
    check: Check,
    mismatch: str,
    known: bool,
) -> tuple[str, ...]:
    """One private structural card, never values, XML, Report data or logs."""
    text = bool(node.text and node.text.strip()) or any(
        child.tail and child.tail.strip() for child in node
    )
    contents = (
        "MIXED"
        if text and len(node)
        else "CHILDREN"
        if len(node)
        else "TEXT"
        if text
        else "EMPTY"
    )
    attributes = (
        ", ".join(_structure_name(name, ns) for name in list(node.attrib)[:4]) or "none"
    )
    # Wrapper attributes do not justify displaying unrelated child fields.
    children = (
        "not inspected"
        if parent in {"league", "team"}
        else ", ".join(_structure_name(child.tag, ns) for child in node[:4]) or "none"
    )
    return (
        f"Check: {check.value} UNVERIFIED",
        f"Parent path: {parent}",
        f"Element: {_structure_name(node.tag, ns)}",
        f"Attribute names (up to four): {attributes}",
        f"Contents: {contents}; child names (up to four): {children}",
        f"Contract mismatch: {mismatch}",
        "Recognition: "
        + (
            "Known field name; unsupported shape"
            if known
            else "Unknown field; semantics unknown"
        ),
    )


def _human(
    report: Report,
    check: Check,
    details: tuple[str, ...],
    confirm: Callable[[Check, tuple[str, ...]], Status],
) -> None:
    report.enter(check)
    status = Status(confirm(check, details))
    report.mark(check, status)
    if status is not Status.PASS:
        report.stop(
            check,
            StopReason.HUMAN_CONFIRMATION_REJECTED
            if status is Status.FAIL
            else StopReason.HUMAN_CONFIRMATION_NOT_COMPLETED,
            # UNKNOWN at the last scoring prompt skips no checks: the
            # independent team/roster branch will still run. REJECT aborts it.
            skipped=check is not Check.HUMAN_ROSTER_COMPLETE
            and (status is Status.FAIL or check is not Check.HUMAN_POSITION_SCOPES),
        )
        raise _Stop()


def _selection(
    report: Report,
    check: Check,
    choose: Callable[[str, tuple[str, ...]], int | None],
    title: str,
    options: tuple[str, ...],
) -> int:
    report.enter(check)
    try:
        index = choose(title, options)
    except SelectionCancelled:
        report.stop(check, StopReason.USER_CANCELLED)
        raise _Stop() from None
    if index is None:
        report.stop(check, StopReason.SELECTION_NOT_COMPLETED)
        raise _Stop()
    return index


def _settings_identity(
    root: ET.Element,
    ns: str,
    key: str,
    report: Report,
) -> tuple[ET.Element, ET.Element, int | None]:
    with _checking(report, Check.SETTINGS_STRUCTURE):
        return _parse_settings_identity(root, ns, key)


def _scoring(
    league: ET.Element,
    settings: ET.Element,
    ns: str,
    report: Report,
    confirm: Callable[[Check, tuple[str, ...]], Status],
    inspect_unsupported: Callable[[tuple[str, ...]], None] | None,
) -> None:
    with _checking(report, Check.SCORING_STRUCTURE):
        rejected = _unsupported_settings(settings, ns)
        if rejected:
            reason = (
                StopReason.UNSUPPORTED_SCORING_CONTAINER
                if settings.attrib
                else StopReason.UNSUPPORTED_SCORING_SETTING
            )
            report.mark(Check.SCORING_STRUCTURE, Status.UNVERIFIED)
            report.stop(Check.SCORING_STRUCTURE, reason)
            if inspect_unsupported is not None:
                inspect_unsupported(
                    tuple(
                        line
                        for node, mismatch, known in rejected
                        for line in _structure(
                            node,
                            parent="league" if node is settings else "league/settings",
                            ns=ns,
                            check=Check.SCORING_STRUCTURE,
                            mismatch=mismatch,
                            known=known,
                        )
                    )
                )
            raise _Stop()
        try:
            code, stats, modifier_by_id, _ = _scoring_structure(league, settings, ns)
        except YahooSettingsUnsupportedError as error:
            _unsupported(report, Check.SCORING_STRUCTURE, StopReason(error.reason))
    with _checking(report, Check.MODIFIER_VALUES):
        try:
            weights = _modifiers(modifier_by_id, ns)
        except YahooSettingsUnsupportedError:
            _unsupported(report, Check.MODIFIER_VALUES)
    scoring: list[str] = [_private("scoring_type", code)]
    scopes: list[str] = []
    with _checking(report, Check.STAT_APPLICABILITY):
        for flag in (
            "uses_fractional_points",
            "uses_negative_points",
            "has_multiweek_championship",
            "uses_median_score",
        ):
            value = _bool_field(settings, flag, ns)
            scoring.append(
                _private(flag, None if value is None else "1" if value else "0")
            )
        try:
            rules = _stat_rules(stats, weights, ns)
        except YahooSettingsUnsupportedError:
            _unsupported(report, Check.STAT_APPLICABILITY)
        for rule in rules:

            def flag_text(value: bool | None) -> str | None:
                return None if value is None else "1" if value else "0"

            scoring.append(
                f"stat={ascii(rule.stat_id)} {_private('name', rule.name)} "
                f"weight={rule.modifier if rule.modifier is not None else 'MISSING'} "
                f"{_private('enabled', flag_text(rule.enabled))} "
                f"{_private('display_only', flag_text(rule.display_only))} "
                + _private(
                    "excluded_from_display", flag_text(rule.excluded_from_display)
                )
            )
            scopes.append(
                f"stat={ascii(rule.stat_id)} {_private('scope', rule.position_type)}"
            )
            for scope in rule.scopes or ():
                scopes.append(
                    f"stat={ascii(rule.stat_id)} "
                    f"{_private('scope', scope.position_type)} "
                    + _private("display_only", flag_text(scope.display_only))
                )
    _human(
        report, Check.HUMAN_POINTS_FORMAT, (_private("scoring_type", code),), confirm
    )
    _human(report, Check.HUMAN_SCORING_COMPLETE, tuple(scoring), confirm)
    _human(report, Check.HUMAN_POSITION_SCOPES, tuple(scopes), confirm)


def _roster_slots(
    settings: ET.Element,
    ns: str,
    report: Report,
    confirm: Callable[[Check, tuple[str, ...]], Status],
) -> dict[str, int]:
    with _checking(report, Check.ROSTER_SLOTS):
        try:
            positions, _ = _slots(settings, ns)
        except YahooSettingsUnsupportedError:
            _unsupported(report, Check.ROSTER_SLOTS)
    _human(
        report,
        Check.HUMAN_ROSTER_SLOTS,
        tuple(
            f"{_private('slot', slot.position)} capacity={slot.capacity} "
            f"{_private('position_type', slot.position_type)}"
            for slot in positions
        ),
        confirm,
    )
    return {slot.position: slot.capacity for slot in positions}


def _roster(
    roster: Roster,
    slots: dict[str, int],
    report: Report,
    confirm: Callable[[Check, tuple[str, ...]], Status],
) -> None:
    details: list[str] = []
    selected_counts: Counter[str] = Counter()
    selected_positions: list[RosterEntry] = []
    players = roster.entries
    with _checking(report, Check.PLAYER_POSITIONS):
        for player in players:
            eligible = player.eligible_positions
            assigned = player.selected_position
            if not eligible or assigned is None or assigned not in slots:
                _unsupported(report, Check.PLAYER_POSITIONS)
            assert eligible is not None and assigned is not None
            selected_counts[assigned] += 1
            selected_positions.append(player)
            flag = player.selected_is_flex
            details.append(
                f"{_private('player', player.name)} "
                f"{_private('player_key', player.provider_player_id)} "
                f"eligible={ascii(list(eligible))} {_private('assigned', assigned)} "
                + _private("is_flex", None if flag is None else "1" if flag else "0")
            )
    if not players:
        report.mark(Check.PLAYER_POSITIONS, Status.UNVERIFIED)
    with _checking(report, Check.ROSTER_COVERAGE):
        coverage = roster.coverage
        coverage_details = [
            _private("reported_coverage_type", coverage.kind),
            _private(
                "reported_date", coverage.date.isoformat() if coverage.date else None
            ),
            _private("reported_week", coverage.week),
        ]
        coverage_known = (
            bool(players)
            and not roster.context_unverified
            and coverage.kind == "date"
            and coverage.date is not None
            and coverage.week is None
        )
        for player in selected_positions:
            player_key = player.provider_player_id
            selected_coverage = player.selected_coverage or RosterCoverage()
            if (
                selected_coverage.kind is not None
                and coverage.kind is not None
                and selected_coverage.kind != coverage.kind
            ) or (
                selected_coverage.date is not None
                and coverage.date is not None
                and selected_coverage.date != coverage.date
            ):
                raise ValueError()
            coverage_known &= selected_coverage == coverage
            selected_date = (
                selected_coverage.date.isoformat() if selected_coverage.date else None
            )
            coverage_details.append(
                f"{_private('player_key', player_key)} "
                f"{_private('selected_coverage_type', selected_coverage.kind)} "
                f"{_private('selected_date', selected_date)} "
                f"{_private('selected_week', selected_coverage.week)}"
            )
    with _checking(report, Check.ROSTER_SLOT_CAPACITY):
        if any(count > slots[position] for position, count in selected_counts.items()):
            raise ValueError()
    if not coverage_known:
        report.mark(Check.ROSTER_COVERAGE, Status.UNVERIFIED)
    if roster.context_unverified:
        _unsupported(report, Check.HUMAN_PLAYER_POSITIONS)
    _human(report, Check.HUMAN_PLAYER_POSITIONS, tuple(details), confirm)
    if coverage_known:
        _human(report, Check.HUMAN_ROSTER_COVERAGE, tuple(coverage_details), confirm)
    else:
        # A human can inspect missing coverage, but cannot certify an absent XML
        # date. Do not invent a date from the computer clock or Yahoo's website.
        report.enter(Check.HUMAN_ROSTER_COVERAGE)
        if confirm(Check.HUMAN_ROSTER_COVERAGE, tuple(coverage_details)) is Status.FAIL:
            report.mark(Check.HUMAN_ROSTER_COVERAGE, Status.FAIL)
            report.stop(
                Check.HUMAN_ROSTER_COVERAGE, StopReason.HUMAN_CONFIRMATION_REJECTED
            )
            raise _Stop()
    _human(
        report,
        Check.HUMAN_ROSTER_COMPLETE,
        tuple(details)
        + (
            f"Returned players={len(players)}; includes assigned slots listed above.",
            "Count agreement does not prove reserve inclusion or complete pagination.",
        ),
        confirm,
    )


def verify_contracts(
    access_token: SecretStr,
    *,
    http_client: httpx.Client,
    report: Report,
    choose: Callable[[str, tuple[str, ...]], int | None],
    confirm: Callable[[Check, tuple[str, ...]], Status],
    inspect_unsupported: Callable[[tuple[str, ...]], None] | None = None,
) -> None:
    """One ephemeral attempt. Human callbacks are private terminal interactions.

    Essential prerequisites and explicit rejections stop subsequent requests.
    Unsupported scoring remains UNVERIFIED while independent checks continue.
    Missing optional coverage can still be inspected privately.
    No retries, refresh, arbitrary endpoint inputs, or export of inspection data.
    """
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with _checking(report, Check.LEAGUE_DISCOVERY):
            leagues = parse_leagues(
                _fetch_xml(
                    http_client,
                    access_token,
                    "users;use_login=1/games;game_keys=nhl/leagues",
                )
            )
            if not leagues or len(
                {league.provider_league_id for league in leagues}
            ) != len(leagues):
                raise ValueError()
            if any(
                league.sport != "nhl"
                or not re.fullmatch(r"[0-9]+\.l\.[0-9]+", league.provider_league_id)
                for league in leagues
            ):
                raise ValueError()
        index = _selection(
            report,
            Check.LEAGUE_DISCOVERY,
            choose,
            "Select your personal NHL league",
            tuple(
                f"{_private('league', league.name)} "
                f"{_private('key', league.provider_league_id)}"
                for league in leagues
            ),
        )
        if not 0 <= index < len(leagues):
            raise ValueError()
        key = leagues[index].provider_league_id
        game = key.split(".l.")[0]
        with _checking(report, Check.SETTINGS_STRUCTURE):
            root, ns = _xml_root(
                _fetch_xml(http_client, access_token, f"league/{key}/settings")
            )
        league, settings, team_count = _settings_identity(root, ns, key, report)
        try:
            _scoring(league, settings, ns, report, confirm, inspect_unsupported)
        except _Stop:
            # Unsupported scoring or an UNKNOWN scoring comparison does not
            # invalidate league identity, roster slots, or authenticated ownership.
            # Local scoring FAIL remains FAIL but cannot block identity reads.
            # Explicit human REJECT aborts; interruptions propagate unchanged.
            if report.failed() and report.active_check in (
                Check.HUMAN_POINTS_FORMAT,
                Check.HUMAN_SCORING_COMPLETE,
                Check.HUMAN_POSITION_SCOPES,
            ):
                raise
        with _checking(report, Check.OWNED_TEAM_MEMBERSHIP):
            owned = [
                team
                for team in parse_my_teams(
                    _fetch_xml(
                        http_client,
                        access_token,
                        f"users;use_login=1/games;game_keys={game}/teams",
                    ),
                    game_key=game,
                )
                if team.provider_league_id == key
            ]
            if not owned:
                raise ValueError()
        with _checking(report, Check.LEAGUE_TEAMS_STRUCTURE):
            league_teams = parse_league_teams(
                _fetch_xml(http_client, access_token, f"league/{key}/teams"),
                league_key=key,
            )
            _match_owned_teams(owned, league_teams)
            teams = {team.provider_team_id: team.name for team in league_teams}
        with _checking(report, Check.LEAGUE_TEAMS_COMPLETENESS):
            if team_count is not None and len(teams) != team_count:
                raise ValueError()
        if team_count is None:
            report.mark(Check.LEAGUE_TEAMS_COMPLETENESS, Status.UNVERIFIED)
        _human(
            report,
            Check.HUMAN_LEAGUE_TEAMS_COMPLETE,
            tuple(
                f"{_private('team', name)} {_private('key', k)}"
                for k, name in teams.items()
            ),
            confirm,
        )
        keys = tuple(team.provider_team_id for team in owned)
        index = _selection(
            report,
            Check.OWNED_TEAM_MEMBERSHIP,
            choose,
            "Select your owned team",
            tuple(_private("team", team.name) for team in owned),
        )
        if not 0 <= index < len(keys):
            raise ValueError()
        # Fetch once after explicit owned-team selection. Scoring/slots cannot
        # certify or block the independent envelope and normalization assertions.
        with _checking(report, Check.ROSTER_STRUCTURE):
            root, ns = _xml_root(
                _fetch_xml(http_client, access_token, f"team/{keys[index]}/roster")
            )
            try:
                roster_node, players = _roster_envelope(root, ns, keys[index])
            except YahooRosterUnsupportedError:
                # The existing guard has rejected this exact wrapper. Inspect
                # only its offending nodes; do not parse again or accept them.
                report.mark(Check.ROSTER_STRUCTURE, Status.UNVERIFIED)
                report.stop(Check.ROSTER_STRUCTURE, StopReason.UNSUPPORTED_STRUCTURE)
                if inspect_unsupported is not None:
                    rejected = _one(_one(root, "team", ns), "roster", ns)
                    details: list[str] = []
                    if rejected.attrib:
                        details.extend(
                            _structure(
                                rejected,
                                parent="team",
                                ns=ns,
                                check=Check.ROSTER_STRUCTURE,
                                mismatch="Attributes are not supported on roster",
                                known=True,
                            )
                        )
                    for child in rejected:
                        if len(details) >= 28:  # At most four seven-line cards.
                            break
                        name = child.tag.split("}")[-1]
                        mismatch = []
                        if child.tag != f"{{{ns}}}{name}":
                            mismatch.append("Unexpected namespace")
                        if name not in _ROSTER_FIELDS:
                            mismatch.append("Unrecognized direct field")
                        if set(child.attrib) - (
                            {"count"} if child.tag == f"{{{ns}}}players" else set()
                        ):
                            mismatch.append(
                                "Attributes are not supported on this field"
                            )
                        if mismatch:
                            details.extend(
                                _structure(
                                    child,
                                    parent="team/roster",
                                    ns=ns,
                                    check=Check.ROSTER_STRUCTURE,
                                    mismatch="; ".join(mismatch),
                                    known=name in _ROSTER_FIELDS,
                                )
                            )
                    inspect_unsupported(tuple(details))
                _unsupported(report, Check.ROSTER_STRUCTURE)
        declared = _one(roster_node, "players", ns).get("count")
        report.mark(
            Check.ROSTER_RETURNED_COUNT,
            Status.PASS if declared is not None else Status.UNVERIFIED,
        )
        with _checking(report, Check.ROSTER_NORMALIZATION):
            try:
                roster = _normalize_roster(roster_node, players, ns, owned[index])
            except YahooRosterUnsupportedError:
                _unsupported(report, Check.ROSTER_NORMALIZATION)
        slots = _roster_slots(settings, ns, report, confirm)
        _roster(roster, slots, report, confirm)

    except _Stop:
        pass
    finally:
        logging.disable(previous_logging)
