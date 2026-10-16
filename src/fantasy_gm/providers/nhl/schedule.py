"""Bounded synthetic-transport NHL adapter; no enabled live transport path."""

import json
import math
import re
from dataclasses import dataclass
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
_ISSUES = frozenset(
    {
        "ACCESS_NOT_ENABLED",
        "INPUT_ERROR",
        "REQUEST_REJECTED",
        "RATE_LIMITED",
        "TIMEOUT",
        "TRANSPORT_ERROR",
        "RESPONSE_TOO_LARGE",
        "INVALID_RESPONSE",
        "UNSUPPORTED_RESPONSE",
        "COHORT_UNVERIFIED",
        "COVERAGE_UNVERIFIED",
        "CONFLICTING_GAME",
        "REQUEST_BUDGET_EXHAUSTED",
        "NO_PROGRESS",
    }
)


class ScheduleError(Exception):
    """An allowlisted reason only, without upstream input or exception text."""

    def __init__(self, code: str) -> None:
        self.code = code if code in _ISSUES else "INVALID_RESPONSE"
        super().__init__(self.code)


def _object(value: object) -> dict[str, object]:
    if not isinstance(value, dict) or not all(isinstance(k, str) for k in value):
        raise ScheduleError("INVALID_RESPONSE")
    return value


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ScheduleError("INVALID_RESPONSE")
        result[key] = value
    return result


def _constant(value: str) -> object:
    raise ScheduleError("INVALID_RESPONSE")


def _json(content: bytes) -> dict[str, object]:
    if len(content) > _MAX_BYTES:
        raise ScheduleError("RESPONSE_TOO_LARGE")
    try:
        return _object(
            json.loads(
                content.decode("utf-8"),
                object_pairs_hook=_pairs,
                parse_constant=_constant,
            )
        )
    except (ValueError, RecursionError):
        raise ScheduleError("INVALID_RESPONSE") from None


def _array(value: object, limit: int = 4096) -> list[object]:
    if not isinstance(value, list) or len(value) > limit:
        raise ScheduleError("INVALID_RESPONSE")
    return value


def _integer(value: object, *, minimum: int = 1) -> int:
    if type(value) is not int or value < minimum or value > 10**16:
        raise ScheduleError("INVALID_RESPONSE")
    return value


def _text(value: object, maximum: int = 256) -> str:
    if not isinstance(value, str) or not 1 <= len(value) <= maximum:
        raise ScheduleError("INVALID_RESPONSE")
    return value


def _date(value: object) -> date:
    try:
        text = _text(value, 10)
        result = date.fromisoformat(text)
        if result.isoformat() != text:
            raise ValueError()
        return result
    except ValueError:
        raise ScheduleError("INVALID_RESPONSE") from None


def _season(value: str) -> None:
    if not re.fullmatch(r"[0-9]{8}", value) or int(value[4:]) != int(value[:4]) + 1:
        raise ScheduleError("INPUT_ERROR")


def _team(value: object) -> ScheduleTeam:
    raw = _object(value)
    try:
        return ScheduleTeam(
            provider="nhl",
            provider_team_id=str(_integer(raw.get("id"))),
            abbreviation=_text(raw.get("abbrev"), 3),
        )
    except ValidationError:
        raise ScheduleError("INVALID_RESPONSE") from None


def parse_calendar(content: bytes, *, season: str) -> tuple[ScheduleTeam, ...]:
    """Published catalogue profile; current-season membership is validated."""
    _season(season)
    raw_teams = _array(_json(content).get("teams"), 64)
    result: list[ScheduleTeam] = []
    for value in raw_teams:
        raw = _object(value)
        if _integer(raw.get("seasonId")) != int(season):
            raise ScheduleError("INVALID_RESPONSE")
        team = _team(raw)
        name: str | None = None
        if isinstance(raw.get("name"), dict):
            supplied = _object(raw["name"]).get("default")
            if isinstance(supplied, str) and len(supplied) <= 256:
                name = supplied
        result.append(team.model_copy(update={"name": name}))
    if (
        len(result) != 32
        or len({t.provider_team_id for t in result}) != 32
        or len({t.abbreviation for t in result}) != 32
    ):
        raise ScheduleError("INVALID_RESPONSE")
    return tuple(result)


def _optional_code(value: object) -> str | None:
    return value if isinstance(value, str) and 1 <= len(value) <= 32 else None


def _instant(value: object) -> datetime | None:
    if not isinstance(value, str) or len(value) > 64:
        return None
    try:
        result = datetime.fromisoformat(value)
        if result.tzinfo is None or result.utcoffset() is None:
            return None
        return result.astimezone(UTC)
    except (ValueError, OverflowError):
        return None


def _game(raw: dict[str, object], reported_date: date, season: str) -> ScheduledGame:
    if _integer(raw.get("season")) != int(season):
        raise ScheduleError("INVALID_RESPONSE")
    kind = _integer(raw.get("gameType"), minimum=0)
    state = _optional_code(raw.get("gameState"))
    schedule_state = _optional_code(raw.get("gameScheduleState"))
    try:
        return ScheduledGame(
            provider_game_id=str(_integer(raw.get("id"))),
            season=season,
            game_type={
                1: GameType.EXHIBITION,
                2: GameType.REGULAR,
                3: GameType.POSTSEASON,
            }.get(kind, GameType.UNKNOWN),
            game_type_code=str(kind),
            home=_team(raw.get("homeTeam")),
            away=_team(raw.get("awayTeam")),
            reported_date=reported_date,
            start_time_utc=_instant(raw.get("startTimeUTC")),
            state={
                "FUT": GameState.SCHEDULED,
                "LIVE": GameState.IN_PROGRESS,
                "FINAL": GameState.COMPLETED,
                "OFF": GameState.COMPLETED,
            }.get(state or "", GameState.UNKNOWN),
            state_code=state,
            schedule_state_code=schedule_state,
            schedule_normal=schedule_state == "OK",
        )
    except ValidationError:
        raise ScheduleError("INVALID_RESPONSE") from None


@dataclass(frozen=True)
class ParsedWindow:
    games: tuple[ScheduledGame, ...]
    covered_dates: frozenset[date]


def parse_window(content: bytes, *, season: str) -> ParsedWindow:
    """Validate explicit buckets/counts; absence never establishes an empty day."""
    _season(season)
    raw = _json(content)
    games: dict[str, ScheduledGame] = {}
    covered: set[date] = set()
    total = 0
    for value in _array(raw.get("gameWeek"), 64):
        day = _object(value)
        day_date = _date(day.get("date"))
        if day_date in covered:
            raise ScheduleError("INVALID_RESPONSE")
        covered.add(day_date)
        entries = _array(day.get("games"))
        day_games: set[str] = set()
        for entry in entries:
            game = _game(_object(entry), day_date, season)
            if game.provider_game_id in games:
                raise ScheduleError("CONFLICTING_GAME")
            games[game.provider_game_id] = game
            day_games.add(game.provider_game_id)
        count = _integer(day.get("numberOfGames"), minimum=0)
        if count != len(day_games) or len(games) > 4096:
            raise ScheduleError("INVALID_RESPONSE")
        total += count
    if "numberOfGames" in raw and _integer(raw["numberOfGames"], minimum=0) != total:
        raise ScheduleError("INVALID_RESPONSE")
    return ParsedWindow(tuple(games.values()), frozenset(covered))


class NhlScheduleClient:
    """Only an exact in-process MockTransport is accepted in this offline slice.

    There is deliberately no live-enabling environment flag or HTTPTransport.
    Date padding is a candidate retrieval envelope, never qualified coverage.
    """

    def __init__(self, *, transport: httpx.MockTransport | None = None) -> None:
        if type(transport) is not httpx.MockTransport:
            raise ScheduleError("ACCESS_NOT_ENABLED")
        self._client = httpx.Client(
            transport=transport,
            trust_env=False,
            follow_redirects=False,
            timeout=5,
            headers={"Accept": "application/json", "Accept-Encoding": "identity"},
        )
        self._requests = 0
        self._last_request: float | None = None

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self._client.close()

    def _fetch(self, path: str, deadline: float) -> bytes:
        if self._requests >= 12:
            raise ScheduleError("REQUEST_BUDGET_EXHAUSTED")
        if self._last_request is not None:
            pause = max(0.0, self._last_request + 1 - monotonic())
            if pause >= deadline - monotonic():
                raise ScheduleError("TIMEOUT")
            sleep(pause)
        remaining = deadline - monotonic()
        if remaining <= 0:
            raise ScheduleError("TIMEOUT")
        self._last_request = monotonic()
        self._requests += 1
        fetch_deadline = min(deadline, monotonic() + 30)
        try:
            self._client.cookies.clear()
            with self._client.stream(
                "GET",
                "https://api-web.nhle.com/v1/" + path,
                timeout=httpx.Timeout(
                    connect=min(3, remaining),
                    read=min(5, remaining),
                    write=min(5, remaining),
                    pool=min(2, remaining),
                ),
            ) as response:
                if monotonic() >= fetch_deadline:
                    raise ScheduleError("TIMEOUT")
                if response.status_code == 429:
                    raise ScheduleError("RATE_LIMITED")
                if response.status_code != 200:
                    raise ScheduleError("REQUEST_REJECTED")
                if (
                    response.headers.get("Content-Encoding", "identity").lower()
                    != "identity"
                ):
                    raise ScheduleError("UNSUPPORTED_RESPONSE")
                body = bytearray()
                chunks = (
                    iter((response.content,))
                    if response.is_stream_consumed
                    else response.iter_raw(chunk_size=65536)
                )
                for chunk in chunks:
                    if monotonic() >= fetch_deadline:
                        raise ScheduleError("TIMEOUT")
                    if len(body) + len(chunk) > _MAX_BYTES:
                        raise ScheduleError("RESPONSE_TOO_LARGE")
                    body.extend(chunk)
                if monotonic() >= fetch_deadline:
                    raise ScheduleError("TIMEOUT")
                return bytes(body)
        except httpx.TimeoutException:
            raise ScheduleError("TIMEOUT") from None
        except httpx.HTTPError:
            raise ScheduleError("TRANSPORT_ERROR") from None
        finally:
            self._client.cookies.clear()

    def get_schedule(
        self,
        *,
        season: str,
        start: date,
        end: date,
        timezone: ZoneInfo,
        deadline: float,
    ) -> ScheduleSnapshot:
        _season(season)
        try:
            validate_window(start, end)
            # UTC/local boundary guards are intentionally UNQUALIFIED for NHL.
            required = frozenset(
                start + timedelta(days=i) for i in range(-2, (end - start).days + 3)
            )
        except (ValueError, OverflowError):
            raise ScheduleError("INPUT_ERROR") from None
        if not math.isfinite(deadline):
            raise ScheduleError("INPUT_ERROR")
        deadline = min(deadline, monotonic() + 90)
        self._requests, self._last_request = 0, None
        teams: tuple[ScheduleTeam, ...] = ()
        seen: dict[str, ScheduledGame] = {}
        covered: set[date] = set()
        bucket_ids: dict[date, frozenset[str]] = {}
        issues: list[str] = []
        try:
            teams = parse_calendar(
                self._fetch(f"schedule-calendar/{start.isoformat()}", deadline),
                season=season,
            )
            by_id = {t.provider_team_id: t for t in teams}
            while missing := required - covered:
                window = parse_window(
                    self._fetch(f"schedule/{min(missing).isoformat()}", deadline),
                    season=season,
                )
                pending: dict[str, ScheduledGame] = {}
                new_buckets = {
                    day: frozenset(
                        g.provider_game_id
                        for g in window.games
                        if g.reported_date == day
                    )
                    for day in window.covered_dates
                }
                if any(
                    day in bucket_ids and bucket_ids[day] != ids
                    for day, ids in new_buckets.items()
                ):
                    raise ScheduleError("CONFLICTING_GAME")
                for game in window.games:
                    for team in (game.home, game.away):
                        known = by_id.get(team.provider_team_id)
                        if known is None or known.abbreviation != team.abbreviation:
                            raise ScheduleError("INVALID_RESPONSE")
                    canonical = game.model_copy(
                        update={
                            "home": by_id[game.home.provider_team_id],
                            "away": by_id[game.away.provider_team_id],
                        }
                    )
                    if (
                        canonical.provider_game_id in seen
                        and seen[canonical.provider_game_id] != canonical
                    ):
                        raise ScheduleError("CONFLICTING_GAME")
                    pending[canonical.provider_game_id] = canonical
                if not window.covered_dates & missing:
                    raise ScheduleError("NO_PROGRESS")
                if len(seen.keys() | pending.keys()) > 4096:
                    raise ScheduleError("RESPONSE_TOO_LARGE")
                seen.update(pending)
                covered.update(window.covered_dates)
                bucket_ids.update(new_buckets)
        except ScheduleError as error:
            issues.append(error.code)
        # Permission and source-date semantics are deliberately not asserted here.
        return ScheduleSnapshot(
            season=season,
            teams=teams,
            games=tuple(seen.values()),
            covered_dates=frozenset(covered),
            coverage_timezone=None,
            # Valid catalogue shape alone does not certify the actual NHL cohort.
            cohort_verified=False,
            coverage_contract_verified=False,
            issues=tuple(issues),
            observed_at_utc=datetime.now(UTC),
        )
