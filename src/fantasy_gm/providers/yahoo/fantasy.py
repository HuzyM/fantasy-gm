"""Read-only, in-memory Yahoo hockey league and team identities."""

import logging
import re
from collections.abc import Callable
from datetime import date
from xml.etree import ElementTree

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from fantasy_gm.domain.league import League, NonEmptyString
from fantasy_gm.domain.roster import Roster, RosterCoverage, RosterEntry
from fantasy_gm.domain.settings import LeagueSettings
from fantasy_gm.domain.team import Team

# Yahoo's User APIs / Games collection document this user-scoped combination.
# game_keys=nhl is the documented game-code alias for the current hockey season.
# https://sports.yahoo.com/developer/docs/
LEAGUE_DISCOVERY_URL = (
    "https://fantasysports.yahooapis.com/fantasy/v2/"
    "users;use_login=1/games;game_keys=nhl/leagues"
)
_NAMESPACES = {
    "http://fantasysports.yahooapis.com/fantasy/v2/base.rng",
    "https://fantasysports.yahooapis.com/fantasy/v2/base.rng",
}
# Bound discovery and private-verification unencoded XML to 1 MiB.
MAX_LEAGUE_RESPONSE_BYTES = 1024 * 1024
_API_ORIGIN = "https://fantasysports.yahooapis.com/fantasy/v2/"
_READ_PATH = re.compile(
    r"(?:users;use_login=1/games;game_keys=nhl/leagues"
    r"|users;use_login=1/games;game_keys=[0-9]+/teams"
    r"|league/[0-9]+\.l\.[0-9]+/(?:settings|teams)"
    r"|team/[0-9]+\.l\.[0-9]+\.t\.[0-9]+/roster)"
)
# YFPY's Roster model documents both numeric state flags. is_prescoring's
# semantics remain unresolved: retain an explicit uncertainty marker below.
# https://yfpy.uberfastman.com/models/#yfpy.models.Roster
_ROSTER_FIELDS = {
    "coverage_type",
    "date",
    "week",
    "is_editable",
    "is_prescoring",
    "players",
}


class YahooFantasyError(Exception):
    """Sanitized request or parsing error; never carries a response body."""


class YahooRosterUnsupportedError(YahooFantasyError):
    """A roster shape is not supported; carries no XML or dynamic field names."""


class YahooLeagueMetadata(BaseModel):
    """Yahoo field names remain at this boundary."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    league_key: NonEmptyString
    name: NonEmptyString
    game_code: NonEmptyString | None = None
    season: int | None = None

    def to_domain(self) -> League:
        return League(
            provider="yahoo",
            provider_league_id=self.league_key,
            name=self.name,
            sport=self.game_code,
            season=self.season,
        )


def _collection(
    parent: ElementTree.Element, name: str, item_name: str, namespace: str
) -> list[ElementTree.Element]:
    """Validate Yahoo collection wrappers, not optional resource metadata."""
    collections = parent.findall(f"{{{namespace}}}{name}")
    if len(collections) != 1:
        raise ValueError("Missing or duplicate collection")
    collection = collections[0]
    items = list(collection)
    if any(item.tag != f"{{{namespace}}}{item_name}" for item in items):
        raise ValueError("Unexpected collection child")
    declared_count = collection.get("count")
    # Response count describes returned children, not the requested page size.
    # Do not require count when Yahoo omits this attribute.
    if declared_count is not None:
        if not declared_count.isascii() or not declared_count.isdecimal():
            raise ValueError("Invalid collection count")
        if int(declared_count) != len(items):
            raise ValueError("Inconsistent collection count")
    # Do not silently ignore another wrapper with the wrong namespace.
    if any(
        child.tag.split("}")[-1] == name and child is not collection for child in parent
    ):
        raise ValueError("Unexpected collection namespace or duplicate")
    return items


def _field(parent: ElementTree.Element, name: str, namespace: str) -> str | None:
    """Read consumed metadata without ignoring a wrongly namespaced twin."""
    matches = [child for child in parent if child.tag.split("}")[-1] == name]
    if not matches:
        return None
    if len(matches) != 1 or matches[0].tag != f"{{{namespace}}}{name}":
        raise ValueError("Unexpected metadata namespace or duplicate")
    if len(matches[0]):
        raise ValueError("Metadata must be text")
    return matches[0].text


def _one(parent: ElementTree.Element, name: str, ns: str) -> ElementTree.Element:
    matches = [child for child in parent if child.tag.split("}")[-1] == name]
    if len(matches) != 1 or matches[0].tag != f"{{{ns}}}{name}":
        raise ValueError()
    return matches[0]


def _text(parent: ElementTree.Element, name: str, ns: str) -> str:
    value = _field(parent, name, ns)
    if value is None or not value.strip():
        raise ValueError()
    return value


def _number(value: str) -> int:
    if not re.fullmatch(r"[0-9]{1,9}", value):
        raise ValueError()
    return int(value)


def _flag(parent: ElementTree.Element, name: str, ns: str) -> str | None:
    value = _field(parent, name, ns)
    if value is not None and value not in ("0", "1"):
        raise ValueError()
    return value


def _known_children(parent: ElementTree.Element, names: set[str], ns: str) -> bool:
    count_containers = {
        f"{{{ns}}}{name}" for name in ("stats", "stat_position_types", "players")
    }
    return not parent.attrib and all(
        child.tag in {f"{{{ns}}}{name}" for name in names}
        and set(child.attrib) <= ({"count"} if child.tag in count_containers else set())
        for child in parent
    )


def _coverage(
    parent: ElementTree.Element, ns: str
) -> tuple[str | None, str | None, str | None]:
    kind = _field(parent, "coverage_type", ns)
    reported_date = _field(parent, "date", ns)
    if reported_date is not None:
        if date.fromisoformat(reported_date).isoformat() != reported_date:
            raise ValueError()
    week = _field(parent, "week", ns)
    if week is None and any(child.tag.split("}")[-1] == "week" for child in parent):
        week = ""  # A supplied empty week still cannot establish date-only coverage.
    return kind, reported_date, week


def _xml_root(content: bytes) -> tuple[ElementTree.Element, str]:
    """Shared bounded XML envelope validation; callers validate their hierarchy."""
    if len(content) > MAX_LEAGUE_RESPONSE_BYTES:
        raise YahooFantasyError("Yahoo league-discovery response exceeds size limit")
    try:
        text = content.decode("utf-8-sig")
        # NULs can let Expat autodetect BOM-less UTF-16 after UTF-8 decoding,
        # bypassing the textual declaration guard. XML is UTF-8 only here.
        if "\x00" in text or "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise ValueError("DTD/entity declarations are not accepted")
        root = ElementTree.fromstring(text)
        namespace = root.tag.removeprefix("{").split("}")[0]
        if (
            namespace not in _NAMESPACES
            or root.tag != f"{{{namespace}}}fantasy_content"
        ):
            raise ValueError("Unexpected root")
        return root, namespace
    except (UnicodeDecodeError, ElementTree.ParseError, ValueError):
        raise YahooFantasyError("Malformed Yahoo XML response") from None


def parse_leagues(content: bytes) -> list[League]:
    """Parse Yahoo's documented XML hierarchy; discard unneeded metadata."""
    try:
        root, namespace = _xml_root(content)
        user_items = _collection(root, "users", "user", namespace)
        if len(user_items) > 1:
            raise ValueError("Only the logged-in user is supported")
        leagues: list[League] = []
        for user in user_items:
            for game in _collection(user, "games", "game", namespace):
                for item in _collection(game, "leagues", "league", namespace):
                    code = _field(item, "game_code", namespace) or _field(
                        game, "code", namespace
                    )
                    if code is not None and code != "nhl":
                        raise ValueError("Unexpected sport")
                    season = _field(item, "season", namespace) or _field(
                        game, "season", namespace
                    )
                    metadata = YahooLeagueMetadata(
                        league_key=_field(item, "league_key", namespace) or "",
                        name=_field(item, "name", namespace) or "",
                        game_code=code,
                        season=int(season) if season else None,
                    )
                    leagues.append(metadata.to_domain())
        return leagues
    except (UnicodeDecodeError, ElementTree.ParseError, ValueError):
        raise YahooFantasyError("Malformed Yahoo league-discovery response") from None


def _league_game_key(league_key: str) -> str:
    if re.fullmatch(r"[0-9]+\.l\.[0-9]+", league_key) is None:
        raise YahooFantasyError("Invalid Yahoo league identity")
    return league_key.split(".l.")[0]


def _team_identities(parent: ElementTree.Element, ns: str) -> list[Team]:
    """The same collection/identity contract used by the private verifier."""
    teams: list[Team] = []
    seen: set[str] = set()
    for item in _collection(parent, "teams", "team", ns):
        for field in ("team_key", "team_id", "name"):
            if _one(item, field, ns).attrib:
                raise ValueError()
        key = _text(item, "team_key", ns)
        if re.fullmatch(r"[0-9]+\.l\.[0-9]+\.t\.[0-9]+", key) is None or key in seen:
            raise ValueError()
        if _text(item, "team_id", ns) != key.split(".t.")[1]:
            raise ValueError()
        seen.add(key)
        teams.append(
            Team(
                provider="yahoo",
                provider_league_id=key.split(".t.")[0],
                provider_team_id=key,
                name=_text(item, "name", ns),
            )
        )
    return teams


def parse_league_teams(content: bytes, *, league_key: str) -> list[Team]:
    """Normalize returned league teams; never infer missing identities."""
    game = _league_game_key(league_key)
    try:
        root, ns = _xml_root(content)
        league = _one(root, "league", ns)
        if _text(league, "league_key", ns) != league_key:
            raise ValueError()
        if (
            _field(league, "league_id", ns) not in (None, league_key.split(".l.")[1])
            or _field(league, "game_key", ns) not in (None, game)
            or _field(league, "game_code", ns) not in (None, "nhl")
        ):
            raise ValueError()
        teams = _team_identities(league, ns)
        if any(team.provider_league_id != league_key for team in teams):
            raise ValueError()
        count = _field(league, "num_teams", ns)
        if count is not None and _number(count) != len(teams):
            raise ValueError()
        return teams
    except (ValueError, YahooFantasyError):
        raise YahooFantasyError("Malformed Yahoo league-team response") from None


def parse_my_teams(content: bytes, *, game_key: str) -> list[Team]:
    """Read authenticated ownership from the user-scoped season response only."""
    if re.fullmatch(r"[0-9]+", game_key) is None:
        raise YahooFantasyError("Invalid Yahoo game identity")
    try:
        root, ns = _xml_root(content)
        users = _collection(root, "users", "user", ns)
        if len(users) != 1:
            raise ValueError()
        games = _collection(users[0], "games", "game", ns)
        if (
            len(games) != 1
            or _text(games[0], "game_key", ns) != game_key
            or _field(games[0], "code", ns) not in (None, "nhl")
        ):
            raise ValueError()
        teams = _team_identities(games[0], ns)
        if any(_league_game_key(team.provider_league_id) != game_key for team in teams):
            raise ValueError()
        return teams
    except (ValueError, YahooFantasyError):
        raise YahooFantasyError("Malformed Yahoo owned-team response") from None


def _match_owned_teams(owned: list[Team], league_teams: list[Team]) -> None:
    """Every selected owned identity must agree with the league collection."""
    by_key = {team.provider_team_id: team for team in league_teams}
    if any(by_key.get(team.provider_team_id) != team for team in owned):
        raise YahooFantasyError("Inconsistent Yahoo team membership")


def _validate_roster_team(team: Team) -> None:
    _league_game_key(team.provider_league_id)
    if (
        team.provider != "yahoo"
        or re.fullmatch(
            re.escape(team.provider_league_id) + r"\.t\.[0-9]+", team.provider_team_id
        )
        is None
    ):
        raise YahooFantasyError("Invalid Yahoo team identity")


def _roster_identity(
    root: ElementTree.Element, ns: str, key: str
) -> ElementTree.Element:
    team = _one(root, "team", ns)
    if _one(team, "team_key", ns).attrib or _text(team, "team_key", ns) != key:
        raise ValueError()
    if any(c.tag.split("}")[-1] == "team_id" for c in team):
        if _one(team, "team_id", ns).attrib:
            raise ValueError()
    if _field(team, "team_id", ns) not in (None, key.split(".t.")[1]):
        raise ValueError()
    return _one(team, "roster", ns)


def _roster_envelope(
    root: ElementTree.Element, ns: str, key: str
) -> tuple[ElementTree.Element, list[ElementTree.Element]]:
    """Strict verification contract; application observations use identity only."""
    roster = _roster_identity(root, ns, key)
    if not _known_children(roster, _ROSTER_FIELDS, ns):
        raise YahooRosterUnsupportedError("Unsupported Yahoo roster structure")
    for name in ("is_editable", "is_prescoring"):
        if any(c.tag.split("}")[-1] == name for c in roster):
            if _text(roster, name, ns) not in {"0", "1"}:
                raise ValueError()
    return roster, _collection(roster, "players", "player", ns)


def _reported_coverage(parent: ElementTree.Element, ns: str) -> RosterCoverage:
    for field in ("coverage_type", "date", "week"):
        if (
            any(c.tag.split("}")[-1] == field for c in parent)
            and _one(parent, field, ns).attrib
        ):
            raise ValueError()
    kind, reported_date, week = _coverage(parent, ns)
    # An explicitly empty date is invalid, not a date inferred from today.
    if reported_date is None and any(c.tag == f"{{{ns}}}date" for c in parent):
        raise ValueError()
    return RosterCoverage(
        kind=kind,
        date=date.fromisoformat(reported_date) if reported_date is not None else None,
        week=week,
    )


def _eligible_positions(player: ElementTree.Element, ns: str) -> tuple[str, ...] | None:
    if not any(c.tag.split("}")[-1] == "eligible_positions" for c in player):
        return None
    container = _one(player, "eligible_positions", ns)
    if not _known_children(container, {"position"}, ns):
        raise YahooRosterUnsupportedError("Unsupported Yahoo eligibility structure")
    values = []
    for position in container:
        if len(position) or not position.text or not position.text.strip():
            raise ValueError()
        values.append(position.text)
    if len(set(values)) != len(values):
        raise ValueError()
    return tuple(values)


def _professional_team(
    player: ElementTree.Element, ns: str
) -> tuple[str | None, str | None]:
    """Consume optional reported affiliation, never infer it from a player name.

    YFPY documents these player fields, including NHL roster examples:
    https://yfpy.uberfastman.com/query/#get_team_roster_player_info_by_date
    Its Washington example uses Was; PuckAPI's club directory uses WSH.
    No other aliases or numeric editorial-team identity mappings are inferred.
    """
    team_key: str | None = None
    if any(c.tag.split("}")[-1] == "editorial_team_key" for c in player):
        if _one(player, "editorial_team_key", ns).attrib or not re.fullmatch(
            r"nhl\.t\.[0-9]+", _text(player, "editorial_team_key", ns)
        ):
            raise ValueError()
        team_key = _text(player, "editorial_team_key", ns)
    if not any(c.tag.split("}")[-1] == "editorial_team_abbr" for c in player):
        return None, team_key
    if _one(player, "editorial_team_abbr", ns).attrib:
        raise ValueError()
    code = _text(player, "editorial_team_abbr", ns)
    if not re.fullmatch(r"[A-Za-z]{2,3}", code):
        raise ValueError()
    code = code.upper()
    return ("WSH" if code == "WAS" else code), team_key


def _normalize_roster(
    roster: ElementTree.Element,
    players: list[ElementTree.Element],
    ns: str,
    team: Team,
    *,
    strict: bool = True,
) -> Roster:
    entries: list[RosterEntry] = []
    professional_keys: list[str | None] = []
    seen: set[str] = set()
    game = _league_game_key(team.provider_league_id)
    context_unverified = any(c.tag == f"{{{ns}}}is_prescoring" for c in roster)
    if not strict:
        context_unverified |= not _known_children(roster, _ROSTER_FIELDS, ns)
        for flag in ("is_editable", "is_prescoring"):
            try:
                if any(c.tag.split("}")[-1] == flag for c in roster) and _text(
                    roster, flag, ns
                ) not in {"0", "1"}:
                    context_unverified = True
            except ValueError:
                context_unverified = True
    for player in players:
        for name in ("player_key", "player_id"):
            if _one(player, name, ns).attrib:
                raise ValueError()
        key = _text(player, "player_key", ns)
        if (
            re.fullmatch(re.escape(game) + r"\.p\.[0-9]+", key) is None
            or key in seen
            or _text(player, "player_id", ns) != key.split(".p.")[1]
        ):
            raise ValueError()
        seen.add(key)
        name_node = _one(player, "name", ns)
        if name_node.attrib or _one(name_node, "full", ns).attrib:
            raise ValueError()
        name = _text(name_node, "full", ns)
        eligible: tuple[str, ...] | None = None
        try:
            eligible = _eligible_positions(player, ns)
        except (ValueError, YahooRosterUnsupportedError):
            if strict:
                raise
            context_unverified = True
        selected_position: str | None = None
        selected_coverage: RosterCoverage | None = None
        selected_is_flex: bool | None = None
        if any(c.tag.split("}")[-1] == "selected_position" for c in player):
            try:
                selected = _one(player, "selected_position", ns)
                if not _known_children(
                    selected,
                    {"coverage_type", "date", "week", "position", "is_flex"},
                    ns,
                ):
                    if strict:
                        raise YahooRosterUnsupportedError(
                            "Unsupported Yahoo selected-position structure"
                        )
                    context_unverified = True
            except ValueError:
                if strict:
                    raise
                selected = None
                context_unverified = True
            if selected is not None:
                try:
                    if any(c.tag.split("}")[-1] == "position" for c in selected):
                        if _one(selected, "position", ns).attrib:
                            raise ValueError()
                        selected_position = _text(selected, "position", ns)
                except ValueError:
                    if strict:
                        raise
                    context_unverified = True
                try:
                    selected_coverage = _reported_coverage(selected, ns)
                except ValueError:
                    if strict:
                        raise
                    context_unverified = True
                try:
                    if (
                        any(c.tag.split("}")[-1] == "is_flex" for c in selected)
                        and _one(selected, "is_flex", ns).attrib
                    ):
                        raise ValueError()
                    flex_flag = _flag(selected, "is_flex", ns)
                    selected_is_flex = None if flex_flag is None else flex_flag == "1"
                except ValueError:
                    if strict:
                        raise
                    context_unverified = True
        professional_team_code: str | None = None
        professional_key: str | None = None
        professional_team_unverified = False
        try:
            professional_team_code, professional_key = _professional_team(player, ns)
            if professional_team_code is None and professional_key is not None:
                # A valid numeric key alone cannot establish an NHL affiliation.
                professional_team_unverified = context_unverified = True
        except ValueError:
            if strict:
                raise
            professional_team_unverified = context_unverified = True
        professional_keys.append(professional_key)
        entries.append(
            RosterEntry(
                provider_player_id=key,
                name=name,
                eligible_positions=eligible,
                selected_position=selected_position,
                selected_coverage=selected_coverage,
                selected_is_flex=selected_is_flex,
                professional_team_code=professional_team_code,
                professional_team_unverified=professional_team_unverified,
            )
        )
    # Check internal consistency, without decoding numeric NHL team identities.
    keys_by_code: dict[str, set[str]] = {}
    codes_by_key: dict[str, set[str]] = {}
    for entry, team_key in zip(entries, professional_keys, strict=True):
        if entry.professional_team_code is not None and team_key is not None:
            keys_by_code.setdefault(entry.professional_team_code, set()).add(team_key)
            codes_by_key.setdefault(team_key, set()).add(entry.professional_team_code)
    conflicts = {code for code, keys in keys_by_code.items() if len(keys) > 1}
    for codes in codes_by_key.values():
        if len(codes) > 1:
            conflicts.update(codes)
    if conflicts:
        if strict:
            raise ValueError()
        context_unverified = True
        entries = [
            entry.model_copy(
                update={
                    "professional_team_code": None,
                    "professional_team_unverified": True,
                }
            )
            if entry.professional_team_code in conflicts
            else entry
            for entry in entries
        ]
    declared = _one(roster, "players", ns).get("count")
    try:
        coverage = _reported_coverage(roster, ns)
    except ValueError:
        if strict:
            raise
        coverage = RosterCoverage()
        context_unverified = True
    return Roster(
        team=team,
        entries=tuple(entries),
        coverage=coverage,
        returned_count=int(declared) if declared is not None else None,
        context_unverified=context_unverified,
    )


def parse_roster(content: bytes, *, team: Team) -> Roster:
    """Normalize one bounded response, without certifying ownership or legality.

    Pure parsing cannot prove ownership; use get_owned_team_roster for retrieval.
    """
    _validate_roster_team(team)
    try:
        root, ns = _xml_root(content)
        roster = _roster_identity(root, ns, team.provider_team_id)
        players = _collection(roster, "players", "player", ns)
        return _normalize_roster(roster, players, ns, team, strict=False)
    except YahooRosterUnsupportedError:
        raise
    except (ValueError, YahooFantasyError):
        raise YahooFantasyError("Malformed Yahoo roster response") from None


class YahooFantasyClient:
    """Human-only GETs. No disk, cache, index, retries, or retained responses."""

    def __init__(self, *, http_client: httpx.Client) -> None:
        self._http_client = http_client

    def list_my_hockey_leagues(self, access_token: SecretStr) -> list[League]:
        return parse_leagues(
            _fetch_xml(
                self._http_client,
                access_token,
                "users;use_login=1/games;game_keys=nhl/leagues",
            )
        )

    def list_league_teams(self, access_token: SecretStr, league_key: str) -> list[Team]:
        """One GET for a league selected from authenticated discovery.

        Returns only normalized identities; no settings, scoring or roster reads.
        The caller owns human consent and a clean, non-recording HTTP client.
        """
        _league_game_key(league_key)
        return parse_league_teams(
            _fetch_xml(self._http_client, access_token, f"league/{league_key}/teams"),
            league_key=league_key,
        )

    def list_my_league_teams(
        self, access_token: SecretStr, league_key: str
    ) -> list[Team]:
        """Return all owned teams in the league, cross-checked in two GETs.

        Empty ownership returns [] after one request. A rename/inconsistency
        between responses rejects the attempt; there is no retry or name matching.
        """
        game = _league_game_key(league_key)
        owned = [
            team
            for team in parse_my_teams(
                _fetch_xml(
                    self._http_client,
                    access_token,
                    f"users;use_login=1/games;game_keys={game}/teams",
                ),
                game_key=game,
            )
            if team.provider_league_id == league_key
        ]
        if owned:
            _match_owned_teams(owned, self.list_league_teams(access_token, league_key))
        return owned

    def get_owned_team_roster(
        self,
        access_token: SecretStr,
        *,
        league_key: str,
        team_key: str | None = None,
        choose_team: Callable[[tuple[Team, ...]], str | None] | None = None,
    ) -> Roster:
        """Two ownership/membership reads then one selected current-roster GET.

        No settings, date parameter, scoring, retries, or retained response state.
        """
        _league_game_key(league_key)
        if (team_key is None) == (choose_team is None):
            raise YahooFantasyError("Select one Yahoo roster selection method")
        if (
            team_key is not None
            and re.fullmatch(re.escape(league_key) + r"\.t\.[0-9]+", team_key) is None
        ):
            raise YahooFantasyError("Invalid Yahoo roster selection")
        owned = self.list_my_league_teams(access_token, league_key)
        if choose_team is not None:
            team_key = choose_team(tuple(owned))
        selected = next(
            (team for team in owned if team.provider_team_id == team_key), None
        )
        if selected is None:
            raise YahooFantasyError("Yahoo roster selection is not an owned team")
        return parse_roster(
            _fetch_xml(self._http_client, access_token, f"team/{team_key}/roster"),
            team=selected,
        )

    def get_league_settings(
        self, access_token: SecretStr, league_key: str
    ) -> LeagueSettings:
        """One independent settings GET; unavailable sections are explicit None."""
        from fantasy_gm.providers.yahoo.settings import parse_league_settings

        _league_game_key(league_key)
        return parse_league_settings(
            _fetch_xml(
                self._http_client, access_token, f"league/{league_key}/settings"
            ),
            league_key=league_key,
        )


def _fetch_xml(http_client: httpx.Client, access_token: SecretStr, path: str) -> bytes:
    """Only the fixed read-only paths used by discovery and the private verifier.

    The caller supplies a clean client (no hooks/cache/retries) and owns consent.
    Responses are neither retained on the client wrapper nor written to disk.
    """
    if _READ_PATH.fullmatch(path) is None:
        raise YahooFantasyError("Unsupported Yahoo resource path")
    if re.fullmatch(r"[-A-Za-z0-9._~+/]+=*", access_token.get_secret_value()) is None:
        raise YahooFantasyError("A valid access token is required")
    # Match the private CLI boundary: HTTP library logs can contain resource keys.
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        with http_client.stream(
            "GET",
            _API_ORIGIN + path,
            headers={
                "Authorization": f"Bearer {access_token.get_secret_value()}",
                "Accept": "application/xml",
                "Cache-Control": "no-store",
                "Accept-Encoding": "identity",
            },
            auth=None,
            timeout=10.0,
            follow_redirects=False,
        ) as response:
            if not response.is_success:
                raise YahooFantasyError(
                    "Yahoo league-discovery request rejected "
                    f"(HTTP {response.status_code})"
                )
            content = bytearray()
            if response.headers.get(
                "Content-Encoding", "identity"
            ).strip().lower() not in ("", "identity"):
                raise YahooFantasyError(
                    "Unsupported Yahoo league-discovery content encoding"
                )
            # Read unencoded XML: no unbounded decompressor or full-body read.
            # Content-Length is ignored; the byte counter is authoritative.
            for chunk in response.iter_raw():
                if len(chunk) > MAX_LEAGUE_RESPONSE_BYTES - len(content):
                    raise YahooFantasyError(
                        "Yahoo league-discovery response exceeds size limit"
                    )
                content.extend(chunk)
    except httpx.RequestError:
        raise YahooFantasyError("Yahoo league-discovery request failed") from None
    finally:
        logging.disable(previous_logging)
    return bytes(content)
