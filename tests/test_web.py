"""Offline boundary tests for the process-local browser application."""

import os
from collections.abc import Iterator
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Never

import pytest
from starlette.testclient import TestClient

from fantasy_gm.web import BrowserSession, create_app


def test_public_window_uses_toronto_date_at_utc_midnight() -> None:
    from fantasy_gm.web.__main__ import _schedule_start

    assert _schedule_start(datetime(2026, 10, 19, 2, 30, tzinfo=UTC)) == date(
        2026, 10, 18
    )


@pytest.mark.parametrize(
    "changes,eligible",
    [
        ({}, True),
        ({"schedule_normal": False}, False),
        ({"state": "COMPLETED"}, False),
        ({"state": "UNKNOWN"}, False),
        ({"game_type": "UNKNOWN"}, False),
        ({"start_time_utc": None}, False),
    ],
)
def test_schedule_display_preserves_upcoming_eligibility(
    monkeypatch: pytest.MonkeyPatch, changes: dict[str, object], eligible: bool
) -> None:
    from fantasy_gm.domain.schedule import GameState, GameType
    from fantasy_gm.web.data import schedule_view
    from tests.test_puckapi_schedule import collect, game

    monkeypatch.setattr("fantasy_gm.providers.puckapi.sleep", lambda _: None)
    if "state" in changes:
        changes["state"] = GameState(str(changes["state"]))
    if "game_type" in changes:
        changes["game_type"] = GameType(str(changes["game_type"]))
    snapshot, _ = collect([game()])
    snapshot = snapshot.model_copy(
        update={"games": (snapshot.games[0].model_copy(update=changes),)}
    )
    view = schedule_view(snapshot, date(2026, 10, 20), date(2026, 10, 22))
    games = [g for day in view["days"] for g in day["games"]]
    if changes.get("start_time_utc", True) is None:
        assert not games
        assert view["teams"][1]["unplaced"] == 1  # BOS, then TOR
    else:
        assert games[0]["upcomingEligible"] is eligible
        assert games[0]["time"] == "2026-10-21T00:00:00+00:00"
        assert view["days"][0]["games"]  # Toronto Oct 20, not UTC Oct 21
        assert view["days"][0]["count"]["state"] != "verified"


@pytest.fixture
def client(tmp_path: Path) -> Iterator[TestClient]:
    (tmp_path / "index.html").write_text("demo", encoding="utf-8")
    with TestClient(
        create_app(port=8765, static_root=tmp_path),
        base_url="http://127.0.0.1:8765",
    ) as browser:
        yield browser


def test_synthetic_status_and_schedule(client: TestClient) -> None:
    assert client.get("/api/status").json() == {
        "mode": "synthetic",
        "yahoo": "disconnected",
        "schedule": "synthetic",
    }
    view = client.get("/api/view").json()
    assert view["source"] == "synthetic"
    assert len(view["schedule"]["days"]) == 7
    assert "synthetic" in " ".join(view["provenance"]).lower()


@pytest.mark.parametrize(
    "headers",
    [
        {"host": "localhost:8765"},
        {"host": "127.0.0.1:9999"},
        {"host": "attacker.example"},
        {"origin": "https://attacker.example"},
        {"origin": "null"},
        {"sec-fetch-site": "cross-site"},
        {"sec-fetch-site": "same-site"},
    ],
)
def test_foreign_boundaries(client: TestClient, headers: dict[str, str]) -> None:
    assert client.get("/api/view", headers=headers).status_code == 403


def test_query_write_and_proxy_rejected(client: TestClient) -> None:
    assert client.get("/api/view?access=secret").status_code == 400
    assert client.post("/api/view").status_code == 405
    assert client.options("/api/view").status_code == 405
    assert client.get("/api/proxy/https://example.com").status_code == 404
    result = client.get("/api/view")
    assert "access-control-allow-origin" not in result.headers
    assert result.headers["cache-control"] == "no-store"
    assert result.headers["referrer-policy"] == "no-referrer"


def test_capability_expiry_and_disconnect(tmp_path: Path) -> None:
    now = [0.0]
    session = BrowserSession(private=True, clock=lambda: now[0])
    secret = session.capability
    session.load({"private-marker": "must-stay-private"})
    with TestClient(
        create_app(port=8765, session=session, static_root=tmp_path),
        base_url="http://127.0.0.1:8765",
    ) as browser:
        assert "private-marker" not in browser.get("/api/status").text
        assert browser.get("/api/view").status_code == 401
        assert (
            browser.get(
                "/api/view", headers={"authorization": "Bearer wrong"}
            ).status_code
            == 401
        )
        auth = {"authorization": "Bearer " + secret}
        assert browser.get("/api/view", headers=auth).json() == {
            "private-marker": "must-stay-private"
        }
        now[0] = 1200.0
        assert browser.get("/api/view", headers=auth).status_code == 401
        assert session.view is None
        assert session.capability == ""
        assert browser.get("/api/status").json()["yahoo"] == "expired"

    session = BrowserSession(private=True)
    session.load({"private-marker": "must-stay-private"})
    auth = {"authorization": "Bearer " + session.capability}
    with TestClient(
        create_app(port=8765, session=session, static_root=tmp_path),
        base_url="http://127.0.0.1:8765",
    ) as browser:
        assert browser.post("/api/disconnect", headers=auth).status_code == 403
        assert (
            browser.post(
                "/api/disconnect", headers={**auth, "origin": "http://127.0.0.1:8765"}
            ).status_code
            == 200
        )
        assert session.view is None and session.capability == ""
        assert browser.get("/api/view", headers=auth).status_code == 401


def test_shutdown_clears_private_data(tmp_path: Path) -> None:
    session = BrowserSession(private=True)
    session.load({"sensitive": "data"})
    with TestClient(create_app(port=8765, session=session, static_root=tmp_path)):
        pass
    assert session.view is None and session.capability == ""


def test_static_boundaries(client: TestClient, tmp_path: Path) -> None:
    (tmp_path / "hidden.env").write_text("secret", encoding="utf-8")
    assert client.get("/").text == "demo"
    for path in ("/hidden.env", "/.env", "/%2e%2e/hidden.env", "/src/test.py"):
        assert client.get(path).status_code in (400, 404)


def test_private_launcher_refuses_noninteractive(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fantasy_gm.web.__main__ import main

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    assert main(["--private", "--interactive"]) == 1


def test_default_launcher_never_reads_credentials_or_loads_providers(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fantasy_gm.web.__main__ as launcher

    def deny(*args: object, **kwargs: object) -> Never:
        raise AssertionError("Default mode must not read environment or providers")

    observed: list[bool] = []

    def serve(args: object, session: BrowserSession) -> None:
        observed.append(
            not session.private
            and session.view is not None
            and session.view["source"] == "synthetic"
        )

    original_get = os.environ.get

    def environment_get(key: str, default: str | None = None) -> str | None:
        if key.startswith(("YAHOO_", "PUCKAPI_")):
            deny()
        return original_get(key, default)

    monkeypatch.setattr(os.environ, "get", environment_get)
    monkeypatch.setattr(launcher, "_load_private", deny)
    monkeypatch.setattr(launcher, "_load_public_schedule", deny)
    monkeypatch.setattr(launcher, "_serve", serve)
    assert launcher.main([]) == 0
    assert observed == [True]


def test_duplicate_headers_and_error_reflection(client: TestClient) -> None:
    assert (
        client.get(
            "/api/view",
            headers=[("host", "127.0.0.1:8765"), ("host", "attacker.example")],
        ).status_code
        == 403
    )
    result = client.get("/api/view?secret=private-marker")
    assert "private-marker" not in result.text
    assert (
        client.get(
            "/api/status",
            headers={
                "origin": "http://127.0.0.1:8765",
                "sec-fetch-site": "same-origin",
            },
        ).status_code
        == 200
    )


def test_private_api_does_not_read_disk_or_invoke_providers(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import fantasy_gm.web.__main__ as launcher

    def deny(*args: object, **kwargs: object) -> Never:
        raise AssertionError("API reads must remain memory-only")

    session = BrowserSession(private=True)
    session.load({"mode": "private", "display": "fabricated-private-marker"})
    monkeypatch.setattr(Path, "read_bytes", deny)
    monkeypatch.setattr(Path, "read_text", deny)
    monkeypatch.setattr(launcher, "_load_private", deny)
    monkeypatch.setattr(launcher, "_load_public_schedule", deny)
    with TestClient(
        create_app(port=8765, session=session, static_root=tmp_path),
        base_url="http://127.0.0.1:8765",
    ) as browser:
        result = browser.get(
            "/api/view", headers={"authorization": "Bearer " + session.capability}
        )
        assert result.status_code == 200
        assert "fabricated-private-marker" not in browser.get("/api/status").text


def test_static_symlink_and_junction_guards(
    client: TestClient,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    target = tmp_path / "escape.js"
    target.write_text("sensitive", encoding="utf-8")
    original = Path.is_symlink
    monkeypatch.setattr(Path, "is_symlink", lambda p: p == target or original(p))
    assert client.get("/escape.js").status_code == 404
    monkeypatch.setattr(Path, "is_symlink", original)
    monkeypatch.setattr(Path, "is_junction", lambda p: p == tmp_path)
    assert client.get("/").status_code == 404


def test_adapter_preserves_unverified_affiliation_and_unknown_counts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from fantasy_gm.domain.league import League
    from fantasy_gm.web.data import private_view
    from tests.test_puckapi_schedule import collect, game
    from tests.test_roster_affiliation import roster_with

    monkeypatch.setattr("fantasy_gm.providers.puckapi.sleep", lambda _: None)
    roster = roster_with(b"<editorial_team_key>nba.t.1</editorial_team_key>")
    snapshot, _ = collect([game()])
    league = League(
        provider="yahoo",
        provider_league_id="999.l.77",
        name="Fabricated league",
        season=2026,
        sport="nhl",
    )
    view = private_view(
        league, roster, snapshot, start=date(2026, 10, 20), end=date(2026, 10, 22)
    )
    assert view["roster"]["entries"][0]["scheduleStatus"] == "AFFILIATION_UNVERIFIED"
    assert view["roster"]["entries"][1]["scheduleStatus"] == "MISSING_AFFILIATION"
    assert view["settings"] is None
    assert "provider_league_id" not in str(view)
    assert all(day["count"]["state"] != "verified" for day in view["schedule"]["days"])
    assert all(not team["countComplete"] for team in view["schedule"]["teams"])
