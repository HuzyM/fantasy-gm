"""Read-only discovery of the logged-in user's current Yahoo hockey leagues."""

from xml.etree import ElementTree

import httpx
from pydantic import BaseModel, ConfigDict, SecretStr

from fantasy_gm.domain.league import League, NonEmptyString

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
# A discovery-only response should be small; bound unencoded XML to 1 MiB.
MAX_LEAGUE_RESPONSE_BYTES = 1024 * 1024


class YahooFantasyError(Exception):
    """Sanitized request or parsing error; never carries a response body."""


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


def parse_leagues(content: bytes) -> list[League]:
    """Parse Yahoo's documented XML hierarchy; discard unneeded metadata."""
    if len(content) > MAX_LEAGUE_RESPONSE_BYTES:
        raise YahooFantasyError("Yahoo league-discovery response exceeds size limit")
    try:
        text = content.decode("utf-8-sig")
        if "<!DOCTYPE" in text or "<!ENTITY" in text:
            raise ValueError("DTD/entity declarations are not accepted")
        root = ElementTree.fromstring(text)
        namespace = root.tag.removeprefix("{").split("}")[0]
        if (
            namespace not in _NAMESPACES
            or root.tag != f"{{{namespace}}}fantasy_content"
        ):
            raise ValueError("Unexpected root")
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


class YahooFantasyClient:
    """One GET endpoint only. No disk, cache, index, retries, or retained responses."""

    def __init__(self, *, http_client: httpx.Client) -> None:
        self._http_client = http_client

    def list_my_hockey_leagues(self, access_token: SecretStr) -> list[League]:
        if not access_token.get_secret_value().strip():
            raise YahooFantasyError("An access token is required")
        try:
            with self._http_client.stream(
                "GET",
                LEAGUE_DISCOVERY_URL,
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
        return parse_leagues(bytes(content))
