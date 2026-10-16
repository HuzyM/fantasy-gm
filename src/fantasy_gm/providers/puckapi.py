"""Bounded read-only PuckAPI REST observations; no Yahoo or persistence."""

import json
import logging
import math
import os
import re
from datetime import UTC, date, datetime, timedelta
from time import monotonic, sleep
from types import TracebackType
from typing import Self
from zoneinfo import ZoneInfo

import httpx
from pydantic import ValidationError

from fantasy_gm.domain.schedule import (
    GameState,
    GameType,
    ScheduledGame,
    ScheduleSnapshot,
    ScheduleTeam,
)
from fantasy_gm.sports.nhl.schedule import validate_window

_MAX_BYTES = 2 * 1024 * 1024
# Current provider directory, not a franchise-history or numeric-ID registry.
_CURRENT_CLUBS = frozenset(
    "ANA BOS BUF CAR CBJ CGY CHI COL DAL DET EDM FLA LAK MIN MTL NJD "
    "NSH NYI NYR OTT PHI PIT SEA SJS STL TBL TOR UTA VAN VGK WPG WSH".split()
)
_TYPES = {
    "regular": GameType.REGULAR,
    "playoff": GameType.POSTSEASON,
    "preseason": GameType.EXHIBITION,
}
_STATES = {
    "FUT": GameState.SCHEDULED,
    "LIVE": GameState.IN_PROGRESS,
    "FINAL": GameState.COMPLETED,
    "OFF": GameState.COMPLETED,
}
_ERRORS = frozenset(
    {
        "API_KEY_REQUIRED",
        "INVALID_API_KEY",
        "INPUT_ERROR",
        "AUTHENTICATION_FAILED",
        "CREDITS_EXHAUSTED",
        "RATE_LIMITED",
        "REQUEST_REJECTED",
        "TIMEOUT",
        "TRANSPORT_ERROR",
        "RESPONSE_TOO_LARGE",
        "INVALID_RESPONSE",
        "UNSUPPORTED_RESPONSE",
        "COHORT_UNVERIFIED",
        "COVERAGE_UNVERIFIED",
        "CONFLICTING_GAME",
        "POSSIBLY_TRUNCATED",
        "REQUEST_BUDGET_EXHAUSTED",
    }
)


class PuckApiError(Exception):
    """Fixed diagnostic only; never includes a request, body or secret."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ERRORS else "INVALID_RESPONSE"
        super().__init__(self.code)


def _text(value: object, maximum: int = 64) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise PuckApiError("INVALID_RESPONSE")
    return value


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict):
        raise PuckApiError("INVALID_RESPONSE")
    return value


def _array(value: object, maximum: int) -> list[object]:
    if not isinstance(value, list) or len(value) > maximum:
        raise PuckApiError("INVALID_RESPONSE")
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise PuckApiError("INVALID_RESPONSE")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise PuckApiError("INVALID_RESPONSE")


def _data(content: bytes, secret: str) -> dict[str, object]:
    try:
        raw: object = json.loads(
            content.decode("utf-8"),
            object_pairs_hook=_pairs,
            parse_constant=_constant,
        )
    except (ValueError, UnicodeError, RecursionError):
        raise PuckApiError("INVALID_RESPONSE") from None
    # Reject even escaped/reflected keys before any source strings can be shown.
    pending = [raw]
    while pending:
        value = pending.pop()
        if isinstance(value, str) and secret in value:
            raise PuckApiError("INVALID_RESPONSE")
        if isinstance(value, dict):
            pending.extend(value.keys())
            pending.extend(value.values())
        elif isinstance(value, list):
            pending.extend(value)
    root = _object(raw)
    if "error" in root:
        raise PuckApiError("INVALID_RESPONSE")
    return _object(root.get("data"))


def _date(value: object) -> date:
    try:
        text = _text(value, 10)
        result = date.fromisoformat(text)
        if result.isoformat() != text:
            raise ValueError()
        return result
    except ValueError:
        raise PuckApiError("INVALID_RESPONSE") from None


def _instant(value: object) -> datetime | None:
    # Date plus time and an explicit offset are required. No guessed wall time.
    if not isinstance(value, str) or not re.fullmatch(
        r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}"
        r"(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-5][0-9])",
        value,
    ):
        return None
    try:
        return datetime.fromisoformat(value).astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def _teams(data: dict[str, object]) -> tuple[ScheduleTeam, ...]:
    rows = _array(data.get("teams"), 64)
    count = data.get("count", len(rows))
    if not rows or type(count) is not int or count != len(rows):
        raise PuckApiError("INVALID_RESPONSE")
    result: dict[str, ScheduleTeam] = {}
    try:
        for item in rows:
            raw = _object(item)
            code = _text(raw.get("abbrev"), 3)
            if code in result:
                raise PuckApiError("INVALID_RESPONSE")
            name = raw.get("name")
            result[code] = ScheduleTeam(
                provider="puckapi",
                provider_team_id=code,
                abbreviation=code,
                name=_text(name, 256) if name is not None else None,
            )
    except ValidationError:
        raise PuckApiError("INVALID_RESPONSE") from None
    return tuple(result.values())


def _games(
    data: dict[str, object],
    *,
    teams: tuple[ScheduleTeam, ...],
    season: str,
    first: date,
    last: date,
    game_type: GameType | None,
    limit: int,
) -> tuple[tuple[ScheduledGame, ...], bool]:
    rows = _array(data.get("games"), limit)
    count = data.get("count", len(rows))
    if type(count) is not int or count < len(rows):
        raise PuckApiError("INVALID_RESPONSE")
    by_code = {team.abbreviation: team for team in teams}
    result: dict[str, ScheduledGame] = {}
    try:
        for row in rows:
            raw = _object(row)
            identity = _text(raw.get("id"))
            if identity in result:
                raise PuckApiError("CONFLICTING_GAME")
            reported = _date(raw.get("gameDate"))
            if raw.get("season") != season or not first <= reported <= last:
                raise PuckApiError("INVALID_RESPONSE")
            kind_code = _text(raw.get("gameType"), 32)
            kind = _TYPES.get(kind_code, GameType.UNKNOWN)
            if game_type is not None and kind not in (game_type, GameType.UNKNOWN):
                raise PuckApiError("INVALID_RESPONSE")
            state_code = raw.get("gameState")
            state_code = (
                state_code
                if isinstance(state_code, str) and 1 <= len(state_code) <= 32
                else None
            )
            state = _STATES.get(state_code or "", GameState.UNKNOWN)
            result[identity] = ScheduledGame(
                provider_game_id=identity,
                season=season,
                game_type=kind,
                game_type_code=kind_code,
                home=by_code[_text(raw.get("homeTeam"), 3)],
                away=by_code[_text(raw.get("awayTeam"), 3)],
                reported_date=reported,
                start_time_utc=_instant(raw.get("startTime")),
                state=state,
                state_code=state_code,
                schedule_state_code=None,
                schedule_normal=state != GameState.UNKNOWN,
            )
    except (KeyError, ValidationError):
        raise PuckApiError("INVALID_RESPONSE") from None
    return tuple(result.values()), len(rows) >= limit or count > len(rows)


class PuckApiScheduleClient:
    """Owned REST client. Credentials exist only for this process lifetime."""

    def __init__(
        self,
        *,
        api_key: str,
        transport: httpx.MockTransport | None = None,
    ) -> None:
        if not api_key:
            raise PuckApiError("API_KEY_REQUIRED")
        if len(api_key) > 4096 or not re.fullmatch(r"[!-~]+", api_key):
            raise PuckApiError("INVALID_API_KEY")
        if transport is not None and type(transport) is not httpx.MockTransport:
            raise PuckApiError("INPUT_ERROR")
        self._api_key = api_key
        self._client = httpx.Client(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=5,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
        )
        self._requests = 0
        self._last_request: float | None = None

    @classmethod
    def from_env(cls, *, transport: httpx.MockTransport | None = None) -> Self:
        return cls(api_key=os.environ.get("PUCKAPI_API_KEY", ""), transport=transport)

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._client.close()
        self._api_key = ""

    def _post(
        self,
        tool: str,
        parameters: dict[str, object],
        deadline: float,
    ) -> dict[str, object]:
        if tool not in ("list_teams", "get_games"):
            raise PuckApiError("INPUT_ERROR")
        if self._requests >= 2:
            raise PuckApiError("REQUEST_BUDGET_EXHAUSTED")
        if self._last_request is not None:
            pause = max(0.0, self._last_request + 6 - monotonic())
            if pause >= deadline - monotonic():
                raise PuckApiError("TIMEOUT")
            sleep(pause)
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise PuckApiError("TIMEOUT")
        self._last_request = monotonic()
        self._requests += 1
        fetch_deadline = min(deadline, monotonic() + 30)
        previous_logging = logging.root.manager.disable
        logging.disable(logging.CRITICAL)
        try:
            self._client.cookies.clear()
            with self._client.stream(
                "POST",
                "https://mcp.puckapi.com/v1/" + tool,
                json=parameters,
                headers={"x-api-key": self._api_key},
                timeout=httpx.Timeout(
                    connect=min(3, remaining),
                    read=min(5, remaining),
                    write=min(5, remaining),
                    pool=min(2, remaining),
                ),
            ) as response:
                if monotonic() >= fetch_deadline:
                    raise PuckApiError("TIMEOUT")
                if response.status_code != 200:
                    raise PuckApiError(
                        {
                            401: "AUTHENTICATION_FAILED",
                            402: "CREDITS_EXHAUSTED",
                            429: "RATE_LIMITED",
                        }.get(response.status_code, "REQUEST_REJECTED")
                    )
                if (
                    response.headers.get("Content-Encoding", "identity").lower()
                    != "identity"
                ):
                    raise PuckApiError("UNSUPPORTED_RESPONSE")
                body = bytearray()
                chunks = (
                    iter((response.content,))
                    if response.is_stream_consumed
                    else response.iter_raw(chunk_size=65536)
                )
                for chunk in chunks:
                    if monotonic() >= fetch_deadline:
                        raise PuckApiError("TIMEOUT")
                    if len(body) + len(chunk) > _MAX_BYTES:
                        raise PuckApiError("RESPONSE_TOO_LARGE")
                    body.extend(chunk)
                if monotonic() >= fetch_deadline:
                    raise PuckApiError("TIMEOUT")
                return _data(bytes(body), self._api_key)
        except httpx.TimeoutException:
            raise PuckApiError("TIMEOUT") from None
        except httpx.HTTPError:
            raise PuckApiError("TRANSPORT_ERROR") from None
        finally:
            self._client.cookies.clear()
            logging.disable(previous_logging)

    def get_schedule(
        self,
        *,
        season: str,
        start: date,
        end: date,
        timezone: ZoneInfo,
        game_type: GameType | None = GameType.REGULAR,
        limit: int = 500,
        deadline: float,
    ) -> ScheduleSnapshot:
        try:
            validate_window(start, end)
            if (
                not re.fullmatch(r"[0-9]{8}", season)
                or int(season[4:]) != int(season[:4]) + 1
            ):
                raise ValueError()
            if (
                type(limit) is not int
                or not 1 <= limit <= 500
                or not math.isfinite(deadline)
            ):
                raise ValueError()
            if game_type is not None and game_type not in _TYPES.values():
                raise ValueError()
            # Candidate envelope only; gameDate's timezone is not documented.
            first, last = start - timedelta(days=3), end + timedelta(days=3)
        except (ValueError, OverflowError):
            raise PuckApiError("INPUT_ERROR") from None
        deadline = min(deadline, monotonic() + 90)
        metadata = self._post("list_teams", {}, deadline)
        teams: tuple[ScheduleTeam, ...] = ()
        games: tuple[ScheduledGame, ...] = ()
        issues = ["COVERAGE_UNVERIFIED"]
        try:
            teams = _teams(metadata)
            parameters: dict[str, object] = dict(
                date_from=first.isoformat(),
                date_to=last.isoformat(),
                season=season,
                limit=limit,
            )
            if game_type is not None:
                parameters["game_type"] = next(
                    k for k, v in _TYPES.items() if v == game_type
                )
            games, truncated = _games(
                self._post("get_games", parameters, deadline),
                teams=teams,
                season=season,
                first=first,
                last=last,
                game_type=game_type,
                limit=limit,
            )
            if truncated:
                issues.append("POSSIBLY_TRUNCATED")
        except PuckApiError as error:
            issues.append(error.code)
        cohort = (
            season == "20262027" and {t.abbreviation for t in teams} == _CURRENT_CLUBS
        )
        if not cohort:
            issues.append("COHORT_UNVERIFIED")
        return ScheduleSnapshot(
            season=season,
            teams=teams,
            games=games,
            covered_dates=frozenset(),
            coverage_timezone=timezone.key,
            cohort_verified=cohort,
            coverage_contract_verified=False,
            issues=tuple(issues),
            observed_at_utc=datetime.now(UTC),
        )
