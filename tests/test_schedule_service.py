"""Session-local public schedule cache; synthetic transport and clock only."""

import json
from datetime import date, timedelta
from zoneinfo import ZoneInfo

import httpx
import pytest

from fantasy_gm.domain.schedule import GameType, ScheduleSnapshot
from fantasy_gm.providers.puckapi import PuckApiScheduleClient
from fantasy_gm.schedule_service import ScheduleService
from tests.test_puckapi_schedule import KEY, clubs, game


def test_repeated_window_uses_one_pair_of_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fantasy_gm.providers.puckapi as puck
    from fantasy_gm.schedule_service import ScheduleService

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    requests: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        data = (
            {"teams": clubs()}
            if request.url.path.endswith("list_teams")
            else {"games": [game()]}
        )
        return httpx.Response(200, json={"data": data})

    def client() -> PuckApiScheduleClient:
        return PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve))

    service = ScheduleService(client_factory=client)
    status, snapshot = service.get_schedule(
        season="20262027",
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert status == "CACHE_MISS" and len(requests) == 2
    status, repeated = service.get_schedule(
        season="20262027",
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert status == "CACHE_HIT" and repeated is snapshot and len(requests) == 2
    assert repeated.issues == ("COVERAGE_UNVERIFIED",)


@pytest.fixture
def session(
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[ScheduleService, list[httpx.Request], list[float], list[str]]:
    import fantasy_gm.providers.puckapi as puck
    import fantasy_gm.schedule_service as schedule_service

    monkeypatch.setattr(puck, "sleep", lambda _: None)
    monkeypatch.setattr(schedule_service, "sleep", lambda _: None, raising=False)
    requests: list[httpx.Request] = []
    clock = [0.0]
    mode = ["normal"]

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("list_teams"):
            return httpx.Response(200, json={"data": {"teams": clubs()}})
        if mode[0] == "error":
            return httpx.Response(402, text="dummy private body")
        params = json.loads(request.content)
        day = date.fromisoformat(params["date_from"]) + timedelta(days=3)
        rows = [
            game(
                season=params["season"],
                gameType=params.get("game_type", "regular"),
                gameDate=day.isoformat(),
                startTime=f"{day}T23:00:00Z",
            )
        ]
        if mode[0] == "malformed":
            rows[0]["id"] = None
        data: dict[str, object] = {"games": rows}
        if mode[0] == "truncated":
            data["count"] = 501
        return httpx.Response(200, json={"data": data})

    def client() -> PuckApiScheduleClient:
        return PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve))

    return (
        ScheduleService(client_factory=client, clock=lambda: clock[0]),
        requests,
        clock,
        mode,
    )


def test_ttl_is_not_extended_by_hits_and_refresh_is_explicit(
    session: tuple[ScheduleService, list[httpx.Request], list[float], list[str]],
) -> None:
    service, calls, clock, _ = session

    def get(refresh: bool = False) -> tuple[str, ScheduleSnapshot]:
        return service.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo("America/Toronto"),
            refresh=refresh,
        )

    assert get()[0] == "CACHE_MISS" and len(calls) == 2
    clock[0] = 3599
    assert get()[0] == "CACHE_HIT" and len(calls) == 2
    clock[0] = 3600
    assert get()[0] == "CACHE_MISS" and len(calls) == 4
    assert get(True)[0] == "CACHE_REFRESH" and len(calls) == 6
    assert get()[0] == "CACHE_HIT" and len(calls) == 6


@pytest.mark.parametrize("mode", ["error", "malformed"])
def test_failures_are_not_cached_and_failed_refresh_never_returns_old_snapshot(
    session: tuple[ScheduleService, list[httpx.Request], list[float], list[str]],
    mode: str,
) -> None:
    service, calls, _, selected = session

    def get(refresh: bool = False) -> tuple[str, ScheduleSnapshot]:
        return service.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo("UTC"),
            refresh=refresh,
        )

    old = get()[1]
    selected[0] = mode
    assert get(True)[1] is not old
    assert get()[0] == "CACHE_MISS" and len(calls) == 6
    selected[0] = "normal"
    assert get()[0] == "CACHE_MISS" and len(calls) == 8


def test_partial_truncation_warning_survives_cache_hit(
    session: tuple[ScheduleService, list[httpx.Request], list[float], list[str]],
) -> None:
    service, calls, _, mode = session
    mode[0] = "truncated"

    def get() -> tuple[str, ScheduleSnapshot]:
        return service.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo("UTC"),
        )

    first = get()[1]
    status, second = get()
    assert status == "CACHE_HIT" and first is second and len(calls) == 2
    assert (
        "POSSIBLY_TRUNCATED" in second.issues and "COVERAGE_UNVERIFIED" in second.issues
    )
    assert not second.coverage_contract_verified and not second.covered_dates


def test_cache_inputs_are_compatible_and_capacity_is_bounded(
    session: tuple[ScheduleService, list[httpx.Request], list[float], list[str]],
) -> None:
    service, calls, _, _ = session
    for day in range(20, 25):
        service.get_schedule(
            season="20262027",
            start=date(2026, 10, day),
            end=date(2026, 10, day),
            timezone=ZoneInfo("UTC"),
        )
    assert len(calls) == 10
    assert (
        service.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 20),
            timezone=ZoneInfo("UTC"),
        )[0]
        == "CACHE_MISS"
    )
    for season, zone, kind, limit in [
        ("20252026", "UTC", GameType.REGULAR, 500),
        ("20262027", "America/Toronto", GameType.REGULAR, 500),
        ("20262027", "UTC", GameType.POSTSEASON, 500),
        ("20262027", "UTC", GameType.REGULAR, 100),
    ]:
        assert (
            service.get_schedule(
                season=season,
                start=date(2026, 10, 20),
                end=date(2026, 10, 20),
                timezone=ZoneInfo(zone),
                game_type=kind,
                limit=limit,
            )[0]
            == "CACHE_MISS"
        )
    assert len(calls) == 20
    service.clear()
    assert not service._cache


@pytest.mark.parametrize("ttl", [0, -1, float("nan"), float("inf")])
def test_invalid_ttl_is_rejected(ttl: float) -> None:
    with pytest.raises(ValueError):
        ScheduleService(ttl_seconds=ttl)


def test_fresh_clients_preserve_session_request_spacing(
    session: tuple[ScheduleService, list[httpx.Request], list[float], list[str]],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fantasy_gm.schedule_service as service_module

    service, _, _, _ = session
    pauses: list[float] = []
    monkeypatch.setattr(service_module, "sleep", pauses.append, raising=False)
    for day in (20, 21):
        service.get_schedule(
            season="20262027",
            start=date(2026, 10, day),
            end=date(2026, 10, day),
            timezone=ZoneInfo("UTC"),
        )
    assert pauses == [6.0]


def test_context_exit_discards_cached_schedules(
    session: tuple[ScheduleService, list[httpx.Request], list[float], list[str]],
) -> None:
    service, _, _, _ = session
    with service:
        service.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo("UTC"),
        )
        assert service._cache and KEY not in repr(service._cache)
    assert not service._cache
