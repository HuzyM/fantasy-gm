"""Synthetic characters through the real Windows getpass path; never a live flow."""

import getpass
import logging
import secrets
import sys
from collections import deque
from collections.abc import Callable
from datetime import datetime, timedelta
from urllib.parse import parse_qs, urlencode, urlsplit

import httpx
import pytest

from fantasy_gm import auth
from fantasy_gm.providers.yahoo.diagnostics import GAME_DIAGNOSTIC_URL
from fantasy_gm.providers.yahoo.fantasy import LEAGUE_DISCOVERY_URL
from fantasy_gm.providers.yahoo.oauth import TOKEN_ENDPOINT
from fantasy_gm.providers.yahoo.session import (
    YahooAuthorizationSession,
    YahooAuthorizationSessionError,
)
from tests.test_yahoo_diagnostics import UnreadResponse
from tests.test_yahoo_fantasy import SYNTHETIC_XML

FAKE_STATE = "fake-state-" + "s" * 32


@pytest.fixture
def windows_console(monkeypatch: pytest.MonkeyPatch) -> Callable[[str], list[str]]:
    if sys.platform != "win32":
        pytest.skip("Exercises CPython's Windows getpass implementation")
    import msvcrt

    characters: deque[str] = deque()
    rendered: list[str] = []

    def get_character() -> str:
        assert characters, "Unexpected extra input read"
        return characters.popleft()

    monkeypatch.setattr(sys, "stdin", sys.__stdin__)
    monkeypatch.setattr(msvcrt, "getwch", get_character)
    monkeypatch.setattr(msvcrt, "putwch", rendered.append)

    def feed(value: str) -> list[str]:
        characters.extend(value)
        return rendered

    return feed


def test_stdlib_crlf_paste_leaves_empty_next_prompt(
    windows_console: Callable[[str], list[str]],
) -> None:
    rendered = windows_console("fake-code\r\nfake-returned-state\r")
    read = getpass.getpass
    assert read("Code: ") == "fake-code"
    assert read("State: ") == ""
    assert read("State again: ") == "fake-returned-state"
    assert "fake-code" not in "".join(rendered)
    assert "fake-returned-state" not in "".join(rendered)


@pytest.fixture
def synthetic_cli(monkeypatch: pytest.MonkeyPatch) -> list[httpx.Request]:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-client-id-for-tests")
    monkeypatch.setattr(secrets, "token_urlsafe", lambda size: FAKE_STATE)
    original_client = httpx.Client
    requests: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if str(request.url) == TOKEN_ENDPOINT:
            return httpx.Response(
                200,
                json={
                    "access_token": "fake-access-token",
                    "refresh_token": "fake-refresh-token",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
            )
        assert str(request.url) == LEAGUE_DISCOVERY_URL
        return httpx.Response(200, stream=httpx.ByteStream(SYNTHETIC_XML))

    def client_factory(*, trust_env: bool) -> httpx.Client:
        assert trust_env is False
        return original_client(transport=httpx.MockTransport(handle), trust_env=False)

    monkeypatch.setattr(httpx, "Client", client_factory)
    return requests


@pytest.mark.parametrize("terminator", ["\r", "\n", "\r\n"])
def test_real_cli_hidden_paste_and_callback_round_trip(
    windows_console: Callable[[str], list[str]],
    synthetic_cli: list[httpx.Request],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    terminator: str,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth", "--diagnose-state"])
    # Callback URLSearchParams/textContent preserve this URL-safe state exactly.
    query = urlencode({"code": "fake-code+&-for-tests", "state": FAKE_STATE})
    callback = parse_qs(query)
    rendered = windows_console(
        callback["code"][0] + terminator + callback["state"][0] + terminator
    )
    assert auth.main() == 0
    assert len(synthetic_cli) == 2
    captured = capsys.readouterr()
    authorization = next(
        line for line in captured.out.splitlines() if line.startswith("https://")
    )
    parameters = parse_qs(urlsplit(authorization).query)
    assert parameters["state"] == [FAKE_STATE]
    assert parameters["code_challenge_method"] == ["S256"]
    body = parse_qs(synthetic_cli[0].content.decode())
    assert body["code"] == callback["code"]
    assert "State received: yes\nState length matches: yes" in captured.out
    assert "Synthetic Hockey One" in captured.out
    for secret in (
        callback["code"][0],
        "fake-access-token",
        "fake-refresh-token",
        body["code_verifier"][0],
    ):
        assert secret not in captured.out + captured.err + "".join(rendered)
    # State occurs only in the existing authorization URL, never input echo/diagnostics.
    assert FAKE_STATE not in "".join(rendered)
    assert FAKE_STATE not in captured.out.replace(authorization, "") + captured.err
    assert ("Empty input received" in captured.err) == (terminator == "\r\n")


@pytest.mark.parametrize(
    "received,length_matches",
    [
        (" " + FAKE_STATE, False),
        (FAKE_STATE + " ", False),
        ("\t" + FAKE_STATE, False),
        ("\x16" + FAKE_STATE, False),
        ("\u200b" + FAKE_STATE, False),
        ("\ud800" + FAKE_STATE, False),
        (FAKE_STATE[:20] + "\r" + FAKE_STATE[20:], False),
        (FAKE_STATE[:20] + "\n" + FAKE_STATE[20:], False),
        (FAKE_STATE[:-1] + "x", True),
        ("fake-stale-" + "x" * 32, True),
    ],
)
def test_real_cli_paste_mismatches_still_fail_closed(
    windows_console: Callable[[str], list[str]],
    synthetic_cli: list[httpx.Request],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    received: str,
    length_matches: bool,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth", "--diagnose-state"])
    windows_console("fake-sensitive-code\r" + received + "\r")
    assert auth.main() == 1
    assert not synthetic_cli
    captured = capsys.readouterr()
    assert "state validation failed" in captured.err
    assert "State received: yes" in captured.out
    expected = "yes" if length_matches else "no"
    assert f"State length matches: {expected}" in captured.out
    assert "fake-sensitive-code" not in captured.out + captured.err
    assert received not in captured.err
    assert "Traceback" not in captured.err


@pytest.mark.parametrize("characters", ["\x03", "fake-code\r\x03", "\r\n\x03"])
def test_real_cli_hidden_cancellation_and_empty_paste(
    windows_console: Callable[[str], list[str]],
    synthetic_cli: list[httpx.Request],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    characters: str,
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth"])
    rendered = windows_console(characters)
    assert auth.main() == 1
    assert not synthetic_cli
    captured = capsys.readouterr()
    assert "Authorization cancelled" in captured.err
    assert "fake-code" not in captured.out + captured.err + "".join(rendered)


def test_real_getpass_fallback_never_echoes(
    synthetic_cli: list[httpx.Request],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    if sys.platform != "win32":
        pytest.skip("Exercises Windows redirected-stdin fallback")
    from io import StringIO

    stdin = StringIO("fake-sensitive-code\nfake-sensitive-state\n")
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth"])
    assert auth.main() == 1
    assert not synthetic_cli and stdin.tell() == 0
    captured = capsys.readouterr()
    assert "hidden input unavailable" in captured.err
    assert "fake-sensitive" not in captured.out + captured.err


@pytest.mark.parametrize("first_attempt", ["cancelled", "mismatched"])
def test_restart_after_failed_input_creates_fresh_session(
    windows_console: Callable[[str], list[str]],
    synthetic_cli: list[httpx.Request],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    first_attempt: str,
) -> None:
    next_state = "fake-state-" + "n" * 32
    states = iter([FAKE_STATE, next_state])
    monkeypatch.setattr(secrets, "token_urlsafe", lambda size: next(states))
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth"])
    suffix = "\x03" if first_attempt == "cancelled" else "fake-wrong-state\r"
    windows_console("fake-code\r" + suffix)
    assert auth.main() == 1
    assert not synthetic_cli
    first = capsys.readouterr()
    windows_console("fake-code\r" + next_state + "\r")
    assert auth.main() == 0
    assert len(synthetic_cli) == 2
    second = capsys.readouterr()
    first_url = next(
        line for line in first.out.splitlines() if line.startswith("https://")
    )
    second_url = next(
        line for line in second.out.splitlines() if line.startswith("https://")
    )
    first_parameters = parse_qs(urlsplit(first_url).query)
    second_parameters = parse_qs(urlsplit(second_url).query)
    assert first_parameters["state"] != second_parameters["state"]
    assert first_parameters["code_challenge"] != second_parameters["code_challenge"]


def test_malformed_unicode_state_is_sanitized_and_consumes_session() -> None:
    session = YahooAuthorizationSession()
    original = session.authorization_parameters()["state"]
    with pytest.raises(YahooAuthorizationSessionError, match="state validation failed"):
        session.consume("\ud800" + original)
    with pytest.raises(YahooAuthorizationSessionError, match="already used"):
        session.consume(original)


@pytest.mark.parametrize(
    "scenario,statuses,expected_calls,exit_status",
    [
        ("accepted", (200, 200), 3, 0),
        ("forbidden", (403, 403), 3, 0),
        ("mixed", (200, 403), 3, 0),
        ("token-rejected", (403, 403), 1, 1),
        ("wrong-state", (403, 403), 0, 1),
        ("cancelled", (403, 403), 0, 1),
    ],
)
def test_real_cli_api_diagnostic_exits_without_restart_or_extra_discovery(
    windows_console: Callable[[str], list[str]],
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scenario: str,
    statuses: tuple[int, int],
    expected_calls: int,
    exit_status: int,
) -> None:
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-client-id-for-tests")
    monkeypatch.setattr(secrets, "token_urlsafe", lambda size: FAKE_STATE)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth", "--diagnose-api"])
    original_client = httpx.Client
    calls: list[httpx.Request] = []
    streams: list[UnreadResponse] = []
    previous_logging = logging.root.manager.disable

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if str(request.url) == TOKEN_ENDPOINT:
            if scenario == "token-rejected":
                return httpx.Response(
                    400,
                    json={
                        "error": "invalid_grant",
                        "error_description": "fake-sensitive-code-and-verifier",
                    },
                )
            return httpx.Response(
                200,
                json={
                    "access_token": "fake-sensitive-access-token",
                    "refresh_token": "fake-sensitive-refresh-token",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
            )
        assert request.headers["Authorization"] == "Bearer fake-sensitive-access-token"
        assert str(request.url) == (
            GAME_DIAGNOSTIC_URL if len(calls) == 2 else LEAGUE_DISCOVERY_URL
        )
        stream = UnreadResponse()
        streams.append(stream)
        return httpx.Response(statuses[len(calls) - 2], stream=stream)

    def client_factory(*, trust_env: bool) -> httpx.Client:
        assert trust_env is False
        return original_client(transport=httpx.MockTransport(handle), trust_env=False)

    monkeypatch.setattr(httpx, "Client", client_factory)
    state = "fake-wrong-state" if scenario == "wrong-state" else FAKE_STATE
    characters = (
        "\x03"
        if scenario == "cancelled"
        else ("fake-sensitive-code\r\n" + state + "\r\n")
    )
    windows_console(characters)
    assert auth.main() == exit_status
    assert logging.root.manager.disable == previous_logging
    assert len(calls) == expected_calls
    assert all(stream.closed for stream in streams)
    captured = capsys.readouterr()
    assert "fake-sensitive" not in captured.out + captured.err
    assert "Synthetic Hockey" not in captured.out
    assert "No hockey leagues" not in captured.out
    summaries = [line for line in captured.out.splitlines() if " | HTTP " in line]
    if exit_status == 0:
        assert len(summaries) == 2
        timestamp = next(
            line.removeprefix("UTC attempt time: ")
            for line in captured.out.splitlines()
            if line.startswith("UTC attempt time:")
        )
        assert datetime.fromisoformat(timestamp).utcoffset() == timedelta(0)
    else:
        assert not summaries
    if scenario == "token-rejected":
        assert "HTTP 400" in captured.err and "category=invalid_grant" in captured.err
        assert "UTC failure time:" in captured.err
