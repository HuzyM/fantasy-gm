"""Human launcher regressions with fabricated provider boundaries only."""

import json
from contextlib import nullcontext
from datetime import datetime, tzinfo
from pathlib import Path
from typing import Any, Self

import httpx
import pytest
from starlette.testclient import TestClient

from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.domain.league import League
from fantasy_gm.providers.puckapi import PuckApiScheduleClient
from fantasy_gm.providers.yahoo.oauth import YahooOAuthClient
from fantasy_gm.web import BrowserSession, create_app
from fantasy_gm.web import __main__ as launcher
from tests.test_puckapi_schedule import KEY, clubs, game
from tests.test_roster_affiliation import roster_with
from tests.test_yahoo_contract_verifier import DISCOVERY, OWNED, ROSTER, TEAMS
from tests.test_yahoo_oauth import exchange, payload


def test_yahoo_only_window_survives_as_an_explicit_api_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    league = League(
        provider="yahoo",
        provider_league_id="999.l.77",
        name="Fabricated league",
        season=2026,
        sport="nhl",
    )
    monkeypatch.setattr(launcher, "_private_terminal", nullcontext)
    monkeypatch.setattr(launcher, "_load_private", lambda: (league, roster_with(b"")))
    monkeypatch.setattr(launcher, "_read_visible_input", lambda _: "2026-12-31")
    views: list[dict[str, Any]] = []

    def serve(args: object, session: BrowserSession) -> None:
        assert session.view is not None
        views.append(session.view)

    monkeypatch.setattr(launcher, "_serve", serve)
    assert launcher.main(["--private", "--interactive"]) == 0
    assert views[0]["planningWindow"] == {
        "start": "2026-12-31",
        "end": "2027-01-06",
        "timezone": "America/Toronto",
    }
    assert views[0]["schedule"] is None
    assert all(
        e["scheduleStatus"] == "UNAVAILABLE" for e in views[0]["roster"]["entries"]
    )


def public_boundary(
    monkeypatch: pytest.MonkeyPatch,
    start: str,
    response: httpx.Response | None = None,
    consent: str = "APPROVE PUBLIC SCHEDULE",
    failure_stage: str = "games",
) -> tuple[list[httpx.Request], list[dict[str, Any]]]:
    requests: list[httpx.Request] = []
    views: list[dict[str, Any]] = []

    def send(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path.endswith("list_teams"):
            if failure_stage == "teams" and response is not None:
                return response
            return httpx.Response(200, json={"data": {"teams": clubs()}})
        return (
            response
            if response is not None
            else httpx.Response(200, json={"data": {"games": [game()]}})
        )

    monkeypatch.setattr(launcher, "_private_terminal", nullcontext)
    monkeypatch.setattr(launcher, "_read_visible_input", lambda _: start)
    monkeypatch.setattr(launcher, "_read_hidden_input", lambda _: consent)
    monkeypatch.setattr("fantasy_gm.providers.puckapi.sleep", lambda _: None)
    monkeypatch.setattr(
        PuckApiScheduleClient,
        "from_env",
        lambda: PuckApiScheduleClient(api_key=KEY, transport=httpx.MockTransport(send)),
    )

    def serve(args: object, session: BrowserSession) -> None:
        assert session.view is not None
        views.append(session.view)

    monkeypatch.setattr(launcher, "_serve", serve)
    return requests, views


def test_confirmed_nondefault_window_uses_only_two_existing_public_requests(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests, views = public_boundary(monkeypatch, "2026-10-20")
    assert launcher.main(["--public-schedule", "--interactive"]) == 0
    assert [request.url.path for request in requests] == [
        "/v1/list_teams",
        "/v1/get_games",
    ]
    assert json.loads(requests[1].content) == {
        "date_from": "2026-10-17",
        "date_to": "2026-10-29",
        "season": "20262027",
        "limit": 500,
        "game_type": "regular",
    }
    assert views[0]["schedule"]["start"] == "2026-10-20"
    assert views[0]["schedule"]["end"] == "2026-10-26"
    assert views[0]["roster"] is None
    assert "six credits" in capsys.readouterr().out


@pytest.mark.parametrize(
    "response",
    [
        httpx.Response(403, text="fabricated-provider-secret"),
        httpx.Response(402, text="fabricated-provider-secret"),
        httpx.Response(200, text="fabricated-provider-secret"),
        httpx.Response(
            200,
            headers={"Content-Encoding": "unsupported"},
            content=b"fabricated-provider-secret",
        ),
    ],
)
@pytest.mark.parametrize("stage,expected_requests", [("teams", 1), ("games", 2)])
def test_requested_load_failure_ends_startup_without_retry_or_fallback(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    response: httpx.Response,
    stage: str,
    expected_requests: int,
) -> None:
    requests, views = public_boundary(
        monkeypatch, "2026-10-20", response, failure_stage=stage
    )
    assert launcher.main(["--public-schedule", "--interactive"]) == 1
    assert len(requests) == expected_requests
    assert not views
    output = capsys.readouterr().out
    assert "could not start" in output
    assert "fabricated-provider-secret" not in output


@pytest.mark.parametrize(
    "selected",
    [
        "2026-02-30",
        "20261020",
        "2026-W43-2",
        "2026-6-1",
        "0001-01-01",
        "9999-12-31",
        "2026-06-29",
        "CANCEL",
        "fabricated-private-input",
    ],
)
def test_invalid_or_unsupported_dates_end_before_public_consent_or_requests(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    selected: str,
) -> None:
    requests, views = public_boundary(monkeypatch, selected)

    def deny(prompt: str) -> str:
        pytest.fail("Invalid input must not reach public consent")

    monkeypatch.setattr(launcher, "_read_hidden_input", deny)
    assert launcher.main(["--public-schedule", "--interactive"]) == 1
    assert not requests and not views
    assert "fabricated-private-input" not in capsys.readouterr().out


def test_refused_public_consent_makes_no_dependent_request_and_shows_cost_first(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    requests, views = public_boundary(monkeypatch, "2026-10-20")

    def refuse(prompt: str) -> str:
        explanation = capsys.readouterr().out
        assert "2026-10-20 through 2026-10-26 inclusive" in explanation
        assert "at most two PuckAPI requests" in explanation
        assert "normally six credits" in explanation
        assert "not a checked balance" in explanation
        assert "no retries, fan-out, balance lookup, purchases" in explanation
        assert not requests
        return "CANCEL"

    monkeypatch.setattr(launcher, "_read_hidden_input", refuse)
    assert launcher.main(["--public-schedule", "--interactive"]) == 1
    assert not requests and not views


@pytest.mark.parametrize(
    "selected,instant,start,end,season",
    [
        (
            "2026-03-08",
            "2026-03-01T12:00:00+00:00",
            "2026-03-08",
            "2026-03-14",
            "20252026",
        ),
        (
            "2026-11-01",
            "2026-10-20T12:00:00+00:00",
            "2026-11-01",
            "2026-11-07",
            "20262027",
        ),
        (
            "2026-12-31",
            "2026-10-20T12:00:00+00:00",
            "2026-12-31",
            "2027-01-06",
            "20262027",
        ),
        (
            "2026-10-29",
            "2026-10-20T12:00:00+00:00",
            "2026-10-29",
            "2026-11-04",
            "20262027",
        ),
        ("", "2026-10-19T02:30:00+00:00", "2026-10-18", "2026-10-24", "20262027"),
        ("", "2027-01-01T02:30:00+00:00", "2026-12-31", "2027-01-06", "20262027"),
    ],
)
def test_launcher_loads_exact_calendar_dates_across_toronto_boundaries(
    monkeypatch: pytest.MonkeyPatch,
    selected: str,
    instant: str,
    start: str,
    end: str,
    season: str,
) -> None:
    class Clock(datetime):
        @classmethod
        def now(cls, tz: tzinfo | None = None) -> Self:
            return cls.fromisoformat(instant)

    monkeypatch.setattr(launcher, "datetime", Clock)
    requests, views = public_boundary(
        monkeypatch, selected, httpx.Response(200, json={"data": {"games": []}})
    )
    assert launcher.main(["--public-schedule", "--interactive"]) == 0
    assert views[0]["planningWindow"] == {
        "start": start,
        "end": end,
        "timezone": "America/Toronto",
    }
    assert len(views[0]["schedule"]["days"]) == 7
    assert views[0]["schedule"]["days"][0]["date"] == start
    assert views[0]["schedule"]["days"][-1]["date"] == end
    assert len(requests) == 2
    assert json.loads(requests[1].content)["season"] == season


@pytest.mark.parametrize(
    "season,selected",
    [
        (None, "2026-10-20"),
        (9999, "2026-10-20"),
        (2025, "2026-12-31"),
        (2026, "2027-07-01"),
    ],
)
def test_unsupported_private_season_window_refuses_dependent_public_load(
    monkeypatch: pytest.MonkeyPatch,
    season: int | None,
    selected: str,
) -> None:
    requests, views = public_boundary(monkeypatch, selected)
    league = League(
        provider="yahoo", provider_league_id="999.l.77", name="Invented", season=season
    )
    monkeypatch.setattr(launcher, "_load_private", lambda: (league, roster_with(b"")))
    assert launcher.main(["--private", "--public-schedule", "--interactive"]) == 1
    assert not requests and not views


def test_refused_private_consent_makes_no_oauth_or_fantasy_request(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(launcher, "_private_terminal", nullcontext)
    monkeypatch.setattr(launcher, "_read_hidden_input", lambda _: "CANCEL")

    def deny(*args: object, **kwargs: object) -> None:
        pytest.fail("Refusal must not authorize or create a provider transport")

    monkeypatch.setattr(launcher, "_authorize", deny)
    monkeypatch.setattr(httpx, "HTTPTransport", deny)
    assert launcher.main(["--private", "--interactive"]) == 1


def test_combined_launcher_keeps_provider_budgets_and_memory_only_api(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    public_requests, _ = public_boundary(monkeypatch, "2026-10-20")
    yahoo_requests: list[httpx.Request] = []
    bodies = iter([DISCOVERY.replace(b"2099", b"2026"), OWNED, TEAMS, ROSTER])

    def yahoo(request: httpx.Request) -> httpx.Response:
        yahoo_requests.append(request)
        if request.method == "POST":
            return httpx.Response(200, json=payload())
        return httpx.Response(200, stream=httpx.ByteStream(next(bodies)))

    monkeypatch.setattr(
        httpx, "HTTPTransport", lambda **kwargs: httpx.MockTransport(yahoo)
    )
    monkeypatch.setattr(
        launcher,
        "_read_hidden_input",
        lambda prompt: (
            "APPROVE PRIVATE BROWSER"
            if "PRIVATE BROWSER" in prompt
            else "APPROVE PUBLIC SCHEDULE"
        ),
    )
    monkeypatch.setattr(
        "fantasy_gm.verify_nhl._read_hidden_input",
        lambda prompt: "NEXT" if "NEXT" in prompt else "1",
    )
    monkeypatch.setattr(
        launcher,
        "_authorize",
        lambda http: (
            exchange(
                YahooOAuthClient(
                    YahooOAuthConfig(client_id="fake-client-id-for-tests"),
                    http_client=http,
                )
            ).access_token
        ),
    )

    def serve(args: object, session: BrowserSession) -> None:
        with TestClient(
            create_app(port=8765, session=session, static_root=tmp_path),
            base_url="http://127.0.0.1:8765",
        ) as browser:
            headers = {"authorization": "Bearer " + session.capability}
            for _ in range(3):
                assert browser.get("/api/status").json()["schedule"] == "observed"
                response = browser.get("/api/view", headers=headers)
                assert response.headers["cache-control"] == "no-store"
                assert response.json()["planningWindow"] == {
                    "start": "2026-10-20",
                    "end": "2026-10-26",
                    "timezone": "America/Toronto",
                }
                assert browser.get("/").status_code == 404
            assert len(yahoo_requests) == 5 and len(public_requests) == 2

    monkeypatch.setattr(launcher, "_serve", serve)
    assert launcher.main(["--private", "--public-schedule", "--interactive"]) == 0
    assert sum(request.method == "POST" for request in yahoo_requests) == 1
    gets = [request for request in yahoo_requests if request.method == "GET"]
    assert len(gets) == 4
    assert sum("/roster" in request.url.path for request in gets) == 1
    assert not any(
        any(
            field in request.url.path
            for field in ("settings", "stats", "ownership", "date=")
        )
        for request in gets
    )
    for request in public_requests:
        assert "999." not in request.content.decode()
        assert "Invented" not in request.content.decode()
