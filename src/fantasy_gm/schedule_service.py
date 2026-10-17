"""One bounded, session-local cache of public PuckAPI schedule observations."""

import math
from collections import OrderedDict
from collections.abc import Callable
from datetime import date
from time import monotonic, sleep
from types import TracebackType
from typing import Literal, Self
from zoneinfo import ZoneInfo

from pydantic import ValidationError

from fantasy_gm.domain.schedule import GameType, ScheduleSnapshot
from fantasy_gm.providers.puckapi import PuckApiError, PuckApiScheduleClient
from fantasy_gm.sports.nhl.schedule import validate_window

CacheStatus = Literal["CACHE_HIT", "CACHE_MISS", "CACHE_REFRESH"]
_Key = tuple[str, date, date, str, GameType | None, int]
_CACHEABLE = {"COVERAGE_UNVERIFIED", "COHORT_UNVERIFIED", "POSSIBLY_TRUNCATED"}


class ScheduleService:
    """At most four immutable snapshots. Never receives a roster or Yahoo key."""

    def __init__(
        self,
        *,
        ttl_seconds: float = 3600,
        client_factory: Callable[[], PuckApiScheduleClient] | None = None,
        clock: Callable[[], float] = monotonic,
    ) -> None:
        if not math.isfinite(ttl_seconds) or ttl_seconds <= 0:
            raise ValueError("INPUT_ERROR")
        self._ttl = ttl_seconds
        self._client_factory = client_factory or PuckApiScheduleClient.from_env
        self._clock = clock
        self._last_load_finished: float | None = None
        self._cache: OrderedDict[_Key, tuple[float, ScheduleSnapshot]] = OrderedDict()

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        self.clear()

    def clear(self) -> None:
        self._cache.clear()

    def get_schedule(
        self,
        *,
        season: str,
        start: date,
        end: date,
        timezone: ZoneInfo,
        game_type: GameType | None = GameType.REGULAR,
        limit: int = 500,
        refresh: bool = False,
    ) -> tuple[CacheStatus, ScheduleSnapshot]:
        validate_window(start, end)
        # bool/int equality must not let an invalid limit hit a valid cache key.
        if type(limit) is not int or not 1 <= limit <= 500:
            raise ValueError("INPUT_ERROR")
        if game_type is not None and (
            not isinstance(game_type, GameType) or game_type == GameType.UNKNOWN
        ):
            raise ValueError("INPUT_ERROR")
        now = self._clock()
        for key, (expires, _) in tuple(self._cache.items()):
            if now >= expires:
                del self._cache[key]
        key = (season, start, end, timezone.key, game_type, limit)
        if refresh:
            self._cache.pop(key, None)
        elif key in self._cache:
            self._cache.move_to_end(key)
            return "CACHE_HIT", self._cache[key][1]
        # Every miss owns a new two-call client; no lifetime request-cap reset.
        if self._last_load_finished is not None:
            sleep(max(0.0, self._last_load_finished + 6 - self._clock()))
        try:
            with self._client_factory() as client:
                snapshot = client.get_schedule(
                    season=season,
                    start=start,
                    end=end,
                    timezone=timezone,
                    game_type=game_type,
                    limit=limit,
                    deadline=monotonic() + 90,
                )
        finally:
            self._last_load_finished = self._clock()
        try:
            snapshot = ScheduleSnapshot.model_validate(snapshot.model_dump())
        except ValidationError:
            raise PuckApiError("INVALID_RESPONSE") from None
        if snapshot.season != season or any(
            t.provider != "puckapi" for t in snapshot.teams
        ):
            raise PuckApiError("INVALID_RESPONSE")
        if not set(snapshot.issues) - _CACHEABLE:
            self._cache[key] = (self._clock() + self._ttl, snapshot)
            while len(self._cache) > 4:
                self._cache.popitem(last=False)
        return ("CACHE_REFRESH" if refresh else "CACHE_MISS"), snapshot
