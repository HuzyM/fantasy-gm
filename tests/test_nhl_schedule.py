"""Synthetic NHL web shapes. No recorded sports data or real requests."""

import json
from datetime import date, timedelta
from time import monotonic
from typing import cast
from zoneinfo import ZoneInfo

import httpx
import pytest

import fantasy_gm.providers.nhl.schedule as adapter
from fantasy_gm.domain.schedule import GameState, GameType
from fantasy_gm.providers.nhl.schedule import (
    NhlScheduleClient,
    ScheduleError,
    parse_calendar,
    parse_window,
)


def teams() -> list[dict[str, object]]:
    return [
        dict(
            id=i + 1,
            seasonId=20262027,
            abbrev=f"A{chr(65 + i // 26)}{chr(65 + i % 26)}",
        )
        for i in range(32)
    ]


def raw_game(**changes: object) -> dict[str, object]:
    result: dict[str, object] = dict(
        id=1,
        season=20262027,
        gameType=2,
        startTimeUTC="2026-11-01T23:00:00Z",
        gameState="FUT",
        gameScheduleState="OK",
        homeTeam=teams()[0],
        awayTeam=teams()[1],
    )
    result.update(changes)
    return result


def payload(*games: dict[str, object]) -> bytes:
    return json.dumps(
        dict(
            gameWeek=[dict(date="2026-11-01", numberOfGames=len(games), games=games)],
            numberOfGames=len(games),
        )
    ).encode()


def test_calendar_requires_unique_current_season_clubs() -> None:
    clubs = parse_calendar(json.dumps(dict(teams=teams())).encode(), season="20262027")
    assert len(clubs) == 32
    assert clubs[0].abbreviation == "AAA"
    for invalid in (
        teams()[:-1],
        teams() + [teams()[0]],
        [dict(t, seasonId=20252026) for t in teams()],
    ):
        with pytest.raises(ScheduleError, match="INVALID_RESPONSE"):
            parse_calendar(json.dumps(dict(teams=invalid)).encode(), season="20262027")


@pytest.mark.parametrize(
    "changes,state,kind",
    [
        ({}, GameState.SCHEDULED, GameType.REGULAR),
        ({"gameState": "OFF", "gameType": 3}, GameState.COMPLETED, GameType.POSTSEASON),
        (
            {"gameState": "PRIVATE_UNSUPPORTED", "gameType": 99},
            GameState.UNKNOWN,
            GameType.UNKNOWN,
        ),
        (
            {"gameState": "PPD", "gameScheduleState": "CNCL"},
            GameState.UNKNOWN,
            GameType.REGULAR,
        ),
    ],
)
def test_normalization_preserves_unknown_codes_without_inventing_semantics(
    changes: dict[str, object],
    state: GameState,
    kind: GameType,
) -> None:
    parsed = parse_window(payload(raw_game(**changes)), season="20262027")
    assert parsed.games[0].state == state
    assert parsed.games[0].game_type == kind
    assert parsed.games[0].provider_game_id == "1"


@pytest.mark.parametrize(
    "changes",
    [
        {"id": True},
        {"id": 1.5},
        {"id": -1},
        {"season": 20252026},
        {"gameType": True},
        {"awayTeam": teams()[0]},
        {"homeTeam": {}},
    ],
)
def test_malformed_required_game_fields_are_not_dropped(
    changes: dict[str, object],
) -> None:
    with pytest.raises(ScheduleError, match="INVALID_RESPONSE"):
        parse_window(payload(raw_game(**changes)), season="20262027")


@pytest.mark.parametrize("instant", [None, "floating", "2026-11-01T12:00:00", 123])
def test_bad_optional_time_stays_unknown(instant: object) -> None:
    window = parse_window(payload(raw_game(startTimeUTC=instant)), season="20262027")
    assert window.games[0].start_time_utc is None


def test_explicit_zero_bucket_is_distinct_from_missing_bucket_or_count() -> None:
    assert parse_window(payload(), season="20262027").covered_dates == frozenset(
        {date(2026, 11, 1)}
    )
    for body in (
        b"{}",
        b'{"gameWeek":null}',
        b'{"gameWeek":[{"date":"2026-11-01","games":[]}]}',
        b'{"gameWeek":[{"date":"2026-11-01","numberOfGames":1,"games":[]}]}',
        b'{"gameWeek":[],"numberOfGames":1}',
        b'{"gameWeek":[],"gameWeek":[]}',
        b'{"gameWeek":NaN}',
        b"\xff",
    ):
        with pytest.raises(ScheduleError, match="INVALID_RESPONSE"):
            parse_window(body, season="20262027")


def test_duplicate_ids_and_count_mismatch_cannot_hide_a_missing_game() -> None:
    with pytest.raises(ScheduleError):
        parse_window(payload(raw_game(), raw_game()), season="20262027")


def test_native_transport_and_no_transport_are_disabled() -> None:
    with pytest.raises(ScheduleError, match="ACCESS_NOT_ENABLED"):
        NhlScheduleClient()
    with pytest.raises(ScheduleError, match="ACCESS_NOT_ENABLED"):
        NhlScheduleClient(transport=cast(httpx.MockTransport, object()))


def test_collection_uses_missing_dates_and_preserves_unqualified_coverage() -> None:
    requests: list[str] = []

    def serve(request: httpx.Request) -> httpx.Response:
        assert request.method == "GET"
        assert request.url.host == "api-web.nhle.com"
        assert "authorization" not in request.headers
        requests.append(request.url.path)
        if "schedule-calendar" in request.url.path:
            return httpx.Response(200, json=dict(teams=teams()))
        day = date.fromisoformat(request.url.path.rsplit("/", 1)[1])
        return httpx.Response(
            200,
            json=dict(
                gameWeek=[
                    dict(
                        date=(day + timedelta(days=i)).isoformat(),
                        numberOfGames=0,
                        games=[],
                    )
                    for i in range(7)
                ],
                numberOfGames=0,
            ),
        )

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 1),
            end=date(2026, 11, 8),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 30,
        )
    assert len(requests) == 3
    assert requests[1:] == ["/v1/schedule/2026-10-30", "/v1/schedule/2026-11-06"]
    # Thirty-two structurally valid invented clubs cannot certify the NHL cohort.
    assert not result.cohort_verified
    assert not result.coverage_contract_verified


@pytest.mark.parametrize(
    "status,code",
    [
        (302, "REQUEST_REJECTED"),
        (403, "REQUEST_REJECTED"),
        (429, "RATE_LIMITED"),
        (500, "REQUEST_REJECTED"),
    ],
)
def test_transport_denial_stops_without_body_disclosure(status: int, code: str) -> None:
    calls = 0

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(
            status,
            content=b"DO_NOT_DISCLOSE",
            headers={"Location": "https://bad.invalid"},
        )

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 1),
            end=date(2026, 11, 1),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 30,
        )
    assert calls == 1
    assert code in result.issues
    assert "DO_NOT_DISCLOSE" not in repr(result)


def test_size_compression_and_timeout_are_sanitized() -> None:
    for response in (
        httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1)),
        httpx.Response(200, headers={"Content-Encoding": "br"}),
    ):
        with NhlScheduleClient(
            transport=httpx.MockTransport(lambda req, response=response: response)
        ) as client:
            result = client.get_schedule(
                season="20262027",
                start=date(2026, 11, 1),
                end=date(2026, 11, 1),
                timezone=ZoneInfo("UTC"),
                deadline=monotonic() + 30,
            )
        assert not result.teams
        assert not result.cohort_verified
        assert result.issues[0] in ("RESPONSE_TOO_LARGE", "UNSUPPORTED_RESPONSE")


def test_expired_deadline_and_invalid_input_never_send() -> None:
    def deny(request: httpx.Request) -> httpx.Response:
        raise AssertionError("must not send")

    with NhlScheduleClient(transport=httpx.MockTransport(deny)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 1),
            end=date(2026, 11, 1),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() - 1,
        )
        assert "TIMEOUT" in result.issues
        with pytest.raises(ScheduleError, match="INPUT_ERROR"):
            client.get_schedule(
                season="../evil",
                start=date(2026, 11, 1),
                end=date(2026, 11, 1),
                timezone=ZoneInfo("UTC"),
                deadline=monotonic() + 30,
            )


@pytest.mark.parametrize("progress", [True, False])
def test_request_budget_and_no_progress_are_bounded(
    monkeypatch: pytest.MonkeyPatch,
    progress: bool,
) -> None:
    monkeypatch.setattr(adapter, "sleep", lambda seconds: None)
    requests: list[str] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request.url.path)
        if "schedule-calendar" in request.url.path:
            return httpx.Response(200, json={"teams": teams()})
        day = request.url.path.rsplit("/", 1)[1] if progress else "2020-01-01"
        return httpx.Response(
            200,
            json={"gameWeek": [dict(date=day, numberOfGames=0, games=[])]},
        )

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 1),
            end=date(2026, 11, 30),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 90,
        )
    assert len(requests) == (12 if progress else 2)
    assert result.issues == (
        ("REQUEST_BUDGET_EXHAUSTED",) if progress else ("NO_PROGRESS",)
    )


def test_transport_failure_retains_prior_window_without_leaking_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "sleep", lambda seconds: None)
    calls = 0

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, json={"teams": teams()})
        if calls == 2:
            return httpx.Response(
                200,
                json={
                    "gameWeek": [
                        dict(
                            date="2026-11-01",
                            numberOfGames=1,
                            games=[raw_game()],
                        )
                    ]
                },
            )
        raise httpx.ReadTimeout("DO_NOT_DISCLOSE")

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 3),
            end=date(2026, 11, 4),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 90,
        )
    assert len(result.games) == 1
    assert result.issues == ("TIMEOUT",)
    assert "DO_NOT_DISCLOSE" not in repr(result)


def test_received_cookies_are_not_sent_on_subsequent_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(adapter, "sleep", lambda seconds: None)

    def serve(request: httpx.Request) -> httpx.Response:
        assert "cookie" not in request.headers
        if "schedule-calendar" in request.url.path:
            return httpx.Response(
                200,
                json={"teams": teams()},
                headers={"Set-Cookie": "synthetic=opaque; Path=/"},
            )
        return httpx.Response(200, json={"gameWeek": []})

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 1),
            end=date(2026, 11, 1),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 90,
        )
    assert result.issues == ("NO_PROGRESS",)


@pytest.mark.parametrize("replacement", [None, 2])
def test_overlapping_bucket_cannot_remove_or_replace_a_game_silently(
    monkeypatch: pytest.MonkeyPatch,
    replacement: int | None,
) -> None:
    monkeypatch.setattr(adapter, "sleep", lambda seconds: None)
    calls = 0

    def serve(request: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        if calls == 1:
            return httpx.Response(200, json={"teams": teams()})
        if calls == 2:
            return httpx.Response(
                200,
                json={
                    "gameWeek": [
                        dict(date="2026-10-30", numberOfGames=0, games=[]),
                        dict(
                            date="2026-10-31",
                            numberOfGames=1,
                            games=[raw_game(startTimeUTC="2026-10-31T23:00:00Z")],
                        ),
                    ]
                },
            )
        changed = (
            []
            if replacement is None
            else [
                raw_game(
                    id=replacement,
                    startTimeUTC="2026-10-31T23:00:00Z",
                )
            ]
        )
        return httpx.Response(
            200,
            json={
                "gameWeek": [
                    dict(date="2026-10-31", numberOfGames=len(changed), games=changed),
                    *(
                        dict(date=f"2026-11-0{i}", numberOfGames=0, games=[])
                        for i in range(1, 4)
                    ),
                ]
            },
        )

    with NhlScheduleClient(transport=httpx.MockTransport(serve)) as client:
        result = client.get_schedule(
            season="20262027",
            start=date(2026, 11, 1),
            end=date(2026, 11, 1),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 90,
        )
    assert result.issues == ("CONFLICTING_GAME",)
    assert [g.provider_game_id for g in result.games] == ["1"]
    assert result.covered_dates == frozenset({date(2026, 10, 30), date(2026, 10, 31)})
    assert calls == 3
