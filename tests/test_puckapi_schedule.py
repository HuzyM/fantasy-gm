"""Fabricated PuckAPI responses and dummy credentials; never recorded games."""

import json
import logging
from collections.abc import Mapping
from datetime import UTC, date, datetime
from time import monotonic
from typing import cast
from zoneinfo import ZoneInfo

import httpx
import pytest

import fantasy_gm.providers.puckapi as adapter
from fantasy_gm.domain.schedule import GameState, GameType, ScheduleSnapshot
from fantasy_gm.providers.puckapi import PuckApiError, PuckApiScheduleClient
from fantasy_gm.sports.nhl.schedule import analyze_schedule

KEY = "dummy-test-key-never-a-credential"
CODES = (
    "ANA BOS BUF CAR CBJ CGY CHI COL DAL DET EDM FLA LAK MIN MTL NJD "
    "NSH NYI NYR OTT PHI PIT SEA SJS STL TBL TOR UTA VAN VGK WPG WSH"
).split()


def clubs() -> list[dict[str, object]]:
    return [dict(abbrev=code, name=f"Invented {i}") for i, code in enumerate(CODES)]


def game(**changes: object) -> dict[str, object]:
    value: dict[str, object] = dict(
        id="900000001",
        season="20262027",
        gameDate="2026-10-20",
        homeTeam="TOR",
        awayTeam="BOS",
        startTime="2026-10-21T00:00:00.000Z",
        gameState="FUT",
        gameType="regular",
    )
    value.update(changes)
    return value


@pytest.fixture(autouse=True)
def no_wait(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adapter, "sleep", lambda _: None)


def collect(
    games: list[dict[str, object]],
    *,
    teams: list[dict[str, object]] | None = None,
    limit: int = 500,
    season: str = "20262027",
    timezone: str = "America/Toronto",
    extra: Mapping[str, object] | None = None,
    kind: GameType | None = GameType.REGULAR,
) -> tuple[ScheduleSnapshot, list[httpx.Request]]:
    requests: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        data = (
            {"teams": clubs() if teams is None else teams}
            if request.url.path.endswith("list_teams")
            else dict(games=games, **(extra or {}))
        )
        return httpx.Response(200, json={"data": data})

    with PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve)) as c:
        snapshot = c.get_schedule(
            season=season,
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo(timezone),
            game_type=kind,
            limit=limit,
            deadline=monotonic() + 90,
        )
    return snapshot, requests


def test_rest_auth_identity_utc_and_observed_analysis() -> None:
    snapshot, requests = collect(
        [
            game(),
            game(
                id="900000002",
                homeTeam="BOS",
                awayTeam="TOR",
                gameDate="2026-10-21",
                startTime="2026-10-21T23:00:00Z",
            ),
        ]
    )
    assert len(requests) == 2
    assert [r.url.path for r in requests] == ["/v1/list_teams", "/v1/get_games"]
    for request in requests:
        assert request.method == "POST"
        assert request.url.host == "mcp.puckapi.com"
        assert request.headers["x-api-key"] == KEY
        assert KEY not in str(request.url) and KEY not in request.content.decode()
        assert "cookie" not in request.headers
    params = json.loads(requests[1].content)
    assert params == dict(
        date_from="2026-10-17",
        date_to="2026-10-25",
        season="20262027",
        game_type="regular",
        limit=500,
    )
    assert snapshot.cohort_verified
    assert not snapshot.coverage_contract_verified and not snapshot.covered_dates
    assert snapshot.games[0].start_time_utc == datetime(2026, 10, 21, tzinfo=UTC)
    assert snapshot.games[0].home.provider_team_id == "TOR"
    report = analyze_schedule(
        snapshot,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    team = next(s for s in report.summaries if s.team.abbreviation == "TOR")
    assert team.total == 2 and team.back_to_back_pairs == (("900000001", "900000002"),)
    assert not team.back_to_back_complete and not report.ranking_available


@pytest.mark.parametrize(
    "instant", [None, "19:30:00", "2026-10-20T19:00:00", "nonsense", 7]
)
def test_missing_or_ambiguous_timestamps_are_unplaced(instant: object) -> None:
    snapshot, _ = collect([game(startTime=instant)])
    assert snapshot.games[0].start_time_utc is None


@pytest.mark.parametrize("offset", ["+00:60", "+01:99", "-00:60"])
def test_malformed_offset_minutes_do_not_become_verified_instants(offset: str) -> None:
    snapshot, _ = collect([game(startTime=f"2026-10-20T20:00:00{offset}")])
    assert snapshot.games[0].start_time_utc is None
    report = analyze_schedule(
        snapshot,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    team = next(s for s in report.summaries if s.team.abbreviation == "TOR")
    assert team.total == 0 and team.unplaced == 1
    assert not team.back_to_back_pairs and not team.count_complete


def test_valid_nonzero_offset_preserves_its_exact_instant() -> None:
    snapshot, _ = collect([game(startTime="2026-10-20T20:00:00+02:30")])
    assert snapshot.games[0].start_time_utc == datetime(
        2026, 10, 20, 17, 30, tzinfo=UTC
    )


def test_empty_response_remains_observed_zero_with_unknown_completeness() -> None:
    snapshot, requests = collect([])
    report = analyze_schedule(
        snapshot,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    assert len(requests) == 2 and snapshot.cohort_verified
    assert snapshot.issues == ("COVERAGE_UNVERIFIED",)
    assert not snapshot.coverage_contract_verified and not snapshot.covered_dates
    assert len(report.summaries) == 32
    assert all(s.total == 0 and not s.count_complete for s in report.summaries)
    assert all(not s.back_to_back_complete for s in report.summaries)
    assert (
        not report.ranking_available
        and not report.most_games
        and not report.fewest_games
    )


def test_local_window_boundaries_keep_b2b_context_out_of_counts() -> None:
    instants = (
        "2026-10-20T03:59:59Z",
        "2026-10-20T04:00:00Z",
        "2026-10-23T03:59:59Z",
        "2026-10-23T04:00:00Z",
    )
    snapshot, _ = collect(
        [
            game(id=str(900000010 + i), gameDate=instant[:10], startTime=instant)
            for i, instant in enumerate(instants)
        ]
    )
    report = analyze_schedule(
        snapshot,
        start=date(2026, 10, 20),
        end=date(2026, 10, 22),
        timezone=ZoneInfo("America/Toronto"),
    )
    team = next(s for s in report.summaries if s.team.abbreviation == "TOR")
    assert team.total == 2
    assert [g.provider_game_id for g in team.games] == ["900000011", "900000012"]
    assert team.back_to_back_pairs == (
        ("900000010", "900000011"),
        ("900000012", "900000013"),
    )
    assert not team.count_complete and not team.back_to_back_complete


@pytest.mark.parametrize("state", [None, "PPD", "CNCL", "RESCHEDULED", "OTHER"])
def test_unsupported_states_are_not_normal(state: object) -> None:
    snapshot, _ = collect([game(gameState=state)])
    assert snapshot.games[0].state == GameState.UNKNOWN
    assert not snapshot.games[0].schedule_normal


@pytest.mark.parametrize(
    "state,expected",
    [
        ("FUT", GameState.SCHEDULED),
        ("LIVE", GameState.IN_PROGRESS),
        ("FINAL", GameState.COMPLETED),
        ("OFF", GameState.COMPLETED),
    ],
)
def test_documented_states(state: str, expected: GameState) -> None:
    snapshot, _ = collect([game(gameState=state)])
    assert snapshot.games[0].state == expected


@pytest.mark.parametrize(
    "changes",
    [
        dict(id=None),
        dict(id=True),
        dict(id=""),
        dict(homeTeam="XXX"),
        dict(homeTeam="BOS"),
        dict(season="20252026"),
        dict(gameDate="bad"),
    ],
)
def test_malformed_identity_or_context_stops_safely(changes: dict[str, object]) -> None:
    snapshot, requests = collect([game(**changes)])
    assert not snapshot.games and "INVALID_RESPONSE" in snapshot.issues
    assert len(requests) == 2


def test_duplicate_ids_do_not_hide_truncation_or_conflicts() -> None:
    snapshot, _ = collect([game(), game()])
    assert "CONFLICTING_GAME" in snapshot.issues
    assert not snapshot.games


def test_conflicting_duplicate_id_does_not_produce_counts() -> None:
    snapshot, requests = collect([game(), game(startTime="2026-10-22T00:00:00Z")])
    assert len(requests) == 2
    assert "CONFLICTING_GAME" in snapshot.issues and not snapshot.games


def test_declared_truncation_below_limit_still_warns() -> None:
    snapshot, requests = collect([game()], extra={"count": 2})
    assert len(requests) == 2 and len(snapshot.games) == 1
    assert "POSSIBLY_TRUNCATED" in snapshot.issues
    assert not snapshot.coverage_contract_verified


@pytest.mark.parametrize("which", ["missing", "wrong", "duplicate", "historical"])
def test_cohort_is_exact_not_merely_32(which: str) -> None:
    teams = clubs()
    season = "20262027"
    if which == "missing":
        teams.pop()
    elif which == "wrong":
        teams[-1]["abbrev"] = "XXX"
    elif which == "duplicate":
        teams[-1] = teams[0]
    else:
        season = "20252026"
    snapshot, _ = collect([], teams=teams, season=season)
    assert not snapshot.cohort_verified
    assert not snapshot.coverage_contract_verified


def test_limit_saturation_and_declared_truncation_do_not_spend_more() -> None:
    for extra in ({}, {"count": 200}):
        snapshot, requests = collect([game()], limit=1, extra=extra)
        assert "POSSIBLY_TRUNCATED" in snapshot.issues
        assert len(requests) == 2
        assert len(snapshot.games) == 1


def test_below_limit_is_not_a_proof_of_full_coverage() -> None:
    snapshot, _ = collect([])
    assert "POSSIBLY_TRUNCATED" not in snapshot.issues
    assert "COVERAGE_UNVERIFIED" in snapshot.issues
    assert not snapshot.covered_dates


@pytest.mark.parametrize(
    "kind,code",
    [
        (GameType.EXHIBITION, "preseason"),
        (GameType.POSTSEASON, "playoff"),
        (None, None),
    ],
)
def test_game_type_filter(kind: GameType | None, code: str | None) -> None:
    snapshot, requests = collect([game(gameType=code or "regular")], kind=kind)
    params = json.loads(requests[1].content)
    assert params.get("game_type") == code
    assert len(snapshot.games) == 1


def test_provider_does_not_silently_accept_wrong_type_or_out_of_query_date() -> None:
    for entry in (game(gameType="playoff"), game(gameDate="2026-09-01")):
        snapshot, _ = collect([entry])
        assert "INVALID_RESPONSE" in snapshot.issues


@pytest.mark.parametrize(
    "status,code",
    [
        (400, "REQUEST_REJECTED"),
        (401, "AUTHENTICATION_FAILED"),
        (402, "CREDITS_EXHAUSTED"),
        (403, "REQUEST_REJECTED"),
        (429, "RATE_LIMITED"),
        (500, "REQUEST_REJECTED"),
        (302, "REQUEST_REJECTED"),
    ],
)
def test_errors_never_retry_or_disclose_body(status: int, code: str) -> None:
    requests: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(
            status, text=KEY, headers={"Location": "https://example.invalid/"}
        )

    with PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve)) as c:
        with pytest.raises(PuckApiError, match=f"^{code}$"):
            c.get_schedule(
                season="20262027",
                start=date(2026, 10, 20),
                end=date(2026, 10, 22),
                timezone=ZoneInfo("UTC"),
                deadline=monotonic() + 90,
            )
    assert len(requests) == 1


@pytest.mark.parametrize("key", [None, "", "x\ny", "x y", "é"])
def test_invalid_or_missing_key_precedes_client_creation(
    key: str | None, monkeypatch: pytest.MonkeyPatch
) -> None:
    if key is None:
        monkeypatch.delenv("PUCKAPI_API_KEY", raising=False)
    else:
        monkeypatch.setenv("PUCKAPI_API_KEY", key)

    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("Client must not be constructed")

    monkeypatch.setattr(httpx, "Client", deny)
    with pytest.raises(PuckApiError, match="API_KEY_REQUIRED|INVALID_API_KEY"):
        PuckApiScheduleClient.from_env()


def test_key_is_read_only_at_runtime(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PUCKAPI_API_KEY", KEY)
    with PuckApiScheduleClient.from_env(
        transport=httpx.MockTransport(
            lambda _: httpx.Response(200, json={"data": {"teams": clubs()}})
        )
    ) as c:
        assert KEY not in repr(c)


def test_http_logging_is_suppressed_and_restored(
    caplog: pytest.LogCaptureFixture,
) -> None:
    previous = logging.root.manager.disable

    def serve(request: httpx.Request) -> httpx.Response:
        logging.getLogger("httpx").critical(KEY)
        return httpx.Response(402, text=KEY)

    with (
        caplog.at_level(logging.DEBUG),
        PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve)) as c,
    ):
        with pytest.raises(PuckApiError):
            c.get_schedule(
                season="20262027",
                start=date(2026, 10, 20),
                end=date(2026, 10, 22),
                timezone=ZoneInfo("UTC"),
                deadline=monotonic() + 90,
            )
    assert KEY not in caplog.text
    assert logging.root.manager.disable == previous


def test_reflected_key_is_not_returned_in_normalized_output() -> None:
    teams = clubs()
    teams[0]["name"] = KEY
    with pytest.raises(PuckApiError, match="^INVALID_RESPONSE$"):
        collect([], teams=teams)


def test_custom_transport_not_accepted() -> None:
    with pytest.raises(PuckApiError):
        PuckApiScheduleClient(
            api_key=KEY, transport=cast(httpx.MockTransport, object())
        )


def test_puckapi_cli_observations_and_undated_games(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    import fantasy_gm.schedule as cli

    requests: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        data = (
            {"teams": clubs()}
            if request.url.path.endswith("list_teams")
            else {"games": [game(), game(id="900000002", startTime="19:30:00")]}
        )
        return httpx.Response(200, json={"data": data})

    def factory(cls: type[PuckApiScheduleClient]) -> PuckApiScheduleClient:
        return cls(api_key=KEY, transport=httpx.MockTransport(serve))

    monkeypatch.setattr(PuckApiScheduleClient, "from_env", classmethod(factory))
    assert (
        cli.main(
            [
                "--puckapi",
                "--season",
                "20262027",
                "--from",
                "2026-10-20",
                "--to",
                "2026-10-22",
            ]
        )
        == 1
    )
    output = capsys.readouterr().out
    assert "PuckAPI" in output and "PARTIAL" in output
    assert "COVERAGE_UNVERIFIED" in output
    assert "2026-10-20T20:00:00-04:00" in output
    assert "source date 2026-10-20" in output and "UTC 2026-10-21" in output
    assert "time unknown" in output and "900000002" in output
    assert "SYNTHETIC" not in output and "complete synthetic" not in output
    assert "Most games" not in output and "Fewest games" not in output
    assert "BOS AWAY" in output and "TOR HOME" in output
    assert len(requests) == 2 and KEY not in output


def test_cli_missing_key_and_invalid_inputs_never_send(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from fantasy_gm.schedule import main

    monkeypatch.delenv("PUCKAPI_API_KEY", raising=False)
    base = [
        "--puckapi",
        "--season",
        "20262027",
        "--from",
        "2026-10-20",
        "--to",
        "2026-10-22",
    ]
    assert main(base) == 2
    assert "API_KEY_REQUIRED" in capsys.readouterr().err
    for extra in (
        ["--demo"],
        ["--limit", "0"],
        ["--limit", "501"],
        ["--timezone", "Missing/Zone"],
    ):
        assert main(base + extra) == 2
        assert not capsys.readouterr().out


@pytest.mark.parametrize(
    "zone,expected",
    [
        ("America/Toronto", "2026-10-20"),
        ("UTC", "2026-10-21"),
        ("Pacific/Auckland", "2026-10-21"),
    ],
)
def test_filtering_uses_instant_in_display_zone(zone: str, expected: str) -> None:
    snapshot, _ = collect([game()], timezone=zone)
    report = analyze_schedule(
        snapshot,
        start=date.fromisoformat(expected),
        end=date.fromisoformat(expected),
        timezone=ZoneInfo(zone),
    )
    assert next(s for s in report.summaries if s.team.abbreviation == "TOR").total == 1
    excluded = analyze_schedule(
        snapshot,
        start=date(2026, 10, 22),
        end=date(2026, 10, 22),
        timezone=ZoneInfo(zone),
    )
    assert all(s.total == 0 for s in excluded.summaries)


@pytest.mark.parametrize(
    "instant,offset",
    [
        ("2026-11-01T05:30:00Z", "-04:00"),
        ("2026-11-01T06:30:00Z", "-05:00"),
        ("2026-03-08T06:30:00Z", "-05:00"),
        ("2026-03-08T07:30:00Z", "-04:00"),
    ],
)
def test_aware_instants_respect_toronto_dst(instant: str, offset: str) -> None:
    parsed = adapter._instant(instant)
    assert parsed is not None
    assert parsed.astimezone(ZoneInfo("America/Toronto")).isoformat().endswith(offset)


@pytest.mark.parametrize(
    "content",
    [
        b'{"data":{},"data":{}}',
        b'{"data": NaN}',
        b"[]",
        b'{"teams":[]}',
        b"\xff",
        b"[" * 1100,
    ],
)
def test_invalid_json_envelopes_fail_without_body(content: bytes) -> None:
    with PuckApiScheduleClient(
        api_key=KEY,
        transport=httpx.MockTransport(lambda _: httpx.Response(200, content=content)),
    ) as c:
        with pytest.raises(PuckApiError, match="^INVALID_RESPONSE$"):
            c.get_schedule(
                season="20262027",
                start=date(2026, 10, 20),
                end=date(2026, 10, 22),
                timezone=ZoneInfo("UTC"),
                deadline=monotonic() + 90,
            )


@pytest.mark.parametrize("code", ["RESPONSE_TOO_LARGE", "TIMEOUT"])
def test_response_limit_and_timeout_are_sanitized(code: str) -> None:
    def serve(request: httpx.Request) -> httpx.Response:
        if code == "TIMEOUT":
            raise httpx.ReadTimeout(KEY, request=request)
        return httpx.Response(200, content=b"x" * (2 * 1024 * 1024 + 1))

    with PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve)) as c:
        with pytest.raises(PuckApiError, match=f"^{code}$"):
            c.get_schedule(
                season="20262027",
                start=date(2026, 10, 20),
                end=date(2026, 10, 22),
                timezone=ZoneInfo("UTC"),
                deadline=monotonic() + 90,
            )


def test_empty_catalogue_does_not_spend_games_credits() -> None:
    snapshot, requests = collect([], teams=[])
    assert not snapshot.teams and len(requests) == 1
    assert "INVALID_RESPONSE" in snapshot.issues


def test_inconsistent_catalogue_count_does_not_qualify() -> None:
    requests: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"data": {"teams": clubs(), "count": 34}})

    with PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve)) as c:
        snapshot = c.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 90,
        )
    assert not snapshot.cohort_verified and len(requests) == 1


def test_cookie_not_forwarded_and_second_request_failure_is_partial() -> None:
    requests: list[httpx.Request] = []

    def serve(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if len(requests) == 1:
            return httpx.Response(
                200,
                json={"data": {"teams": clubs()}},
                headers={"Set-Cookie": "tracking=dummy; Path=/"},
            )
        return httpx.Response(402, text=KEY)

    with PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(serve)) as c:
        snapshot = c.get_schedule(
            season="20262027",
            start=date(2026, 10, 20),
            end=date(2026, 10, 22),
            timezone=ZoneInfo("UTC"),
            deadline=monotonic() + 90,
        )
    assert "CREDITS_EXHAUSTED" in snapshot.issues and snapshot.teams
    assert len(requests) == 2 and "cookie" not in requests[1].headers


def test_candidate_envelope_includes_adjacent_day_b2b_context() -> None:
    snapshot, _ = collect(
        [
            game(gameDate="2026-10-19", startTime="2026-10-19T23:00:00Z"),
            game(id="900000002", startTime="2026-10-20T23:00:00Z"),
        ]
    )
    report = analyze_schedule(
        snapshot,
        start=date(2026, 10, 20),
        end=date(2026, 10, 20),
        timezone=ZoneInfo("America/Toronto"),
    )
    team = next(s for s in report.summaries if s.team.abbreviation == "TOR")
    assert team.total == 1 and team.back_to_back_pairs
    assert not team.back_to_back_complete
