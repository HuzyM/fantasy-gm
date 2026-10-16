"""Private verifier entry point: no credentials, real Yahoo data, or live HTTP."""

import logging
import subprocess
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Never

import httpx
import pytest


def test_help_is_available_without_configuration_or_authentication() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "fantasy_gm.verify_nhl", "--help"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "--interactive" in result.stdout
    assert not result.stderr


@pytest.mark.parametrize("answer", ["CANCEL", "", "approve private read-only"])
def test_no_approval_means_no_configuration_read_or_http(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    answer: str,
) -> None:
    from fantasy_gm import verify_nhl

    @contextmanager
    def terminal() -> Iterator[None]:
        yield

    def forbidden(*args: object, **kwargs: object) -> Never:
        raise AssertionError("Configuration/authentication must not be reached")

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    monkeypatch.setattr(verify_nhl, "_private_terminal", terminal)
    monkeypatch.setattr(verify_nhl, "_read_hidden_input", lambda prompt: answer)
    monkeypatch.setattr(verify_nhl, "_authorize", forbidden)
    assert verify_nhl.main() == 1
    assert "AUTHORIZATION UNVERIFIED" in capsys.readouterr().out


def test_unexpected_private_error_is_sanitized_and_terminal_is_restored(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from fantasy_gm import verify_nhl

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)

    @contextmanager
    def modes() -> Iterator[None]:
        yield

    def fail(*args: object) -> Never:
        raise ValueError("fake-secret-and-private-url-999.l.1001")

    monkeypatch.setattr(verify_nhl, "_terminal_modes", modes)
    monkeypatch.setattr(verify_nhl, "_read_hidden_input", fail)
    assert verify_nhl.main() == 1
    captured = capsys.readouterr()
    assert "fake-secret" not in captured.out + captured.err
    assert "\x1b[?1049h" in captured.out
    assert "\x1b[?1049l" in captured.out
    assert "SESSION FAIL" in captured.out.split("\x1b[?1049l")[1]
    assert not captured.err


@pytest.mark.parametrize(
    "answer,expected",
    [
        ("CONFIRM", "PASS"),
        ("REJECT", "FAIL"),
        ("", "UNVERIFIED"),
        ("yes", "UNVERIFIED"),
        ("UNKNOWN", "UNVERIFIED"),
    ],
)
def test_confirmation_requires_exact_human_input(
    monkeypatch: pytest.MonkeyPatch, answer: str, expected: str
) -> None:
    from fantasy_gm import verify_nhl
    from fantasy_gm.providers.yahoo.contract_verifier import Check

    monkeypatch.setattr(verify_nhl, "_read_hidden_input", lambda prompt: answer)
    assert verify_nhl._confirm(Check.HUMAN_POINTS_FORMAT, ()) == expected


def test_complete_cli_with_synthetic_oauth_and_private_data_only(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    from fantasy_gm import verify_nhl
    from fantasy_gm.providers.yahoo.contract_verifier import Check
    from fantasy_gm.providers.yahoo.oauth import TOKEN_ENDPOINT
    from fantasy_gm.providers.yahoo.session import YahooAuthorizationSession
    from tests.test_yahoo_contract_verifier import PAYLOADS

    session = YahooAuthorizationSession()
    state = session.authorization_parameters()["state"]
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-verifier-client-id")
    monkeypatch.setenv("YAHOO_AI_TOOLS_ENABLED", "false")
    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)

    @contextmanager
    def modes() -> Iterator[None]:
        yield

    monkeypatch.setattr(verify_nhl, "_terminal_modes", modes)
    monkeypatch.setattr(verify_nhl, "YahooAuthorizationSession", lambda: session)

    def answer(prompt: str) -> str:
        if "attest and approve" in prompt:
            return "APPROVE PRIVATE READ-ONLY"
        if "Authorization code" in prompt:
            return "fake-verifier-code"
        if "Returned state" in prompt:
            return state
        if "Selection number" in prompt:
            return "1"
        if "NEXT" in prompt:
            return "NEXT"
        assert "CONFIRM" in prompt
        return "CONFIRM"

    monkeypatch.setattr(verify_nhl, "_read_hidden_input", answer)
    calls: list[httpx.Request] = []
    closed: list[httpx.Response] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        logging.getLogger("fake-private-transport").critical("fake-private-log")
        if len(calls) == 1:
            assert str(request.url) == TOKEN_ENDPOINT and request.method == "POST"
            response = httpx.Response(
                200,
                json={
                    "access_token": "fake-verifier-token",
                    "token_type": "bearer",
                    "expires_in": 3600,
                },
            )
        else:
            response = httpx.Response(
                200, stream=httpx.ByteStream(PAYLOADS[len(calls) - 2])
            )
        closed.append(response)
        return response

    original_client = httpx.Client

    def client_factory(
        *, transport: httpx.BaseTransport, trust_env: bool
    ) -> httpx.Client:
        assert trust_env is False
        transport.close()
        return original_client(transport=httpx.MockTransport(handle), trust_env=False)

    monkeypatch.setattr(httpx, "Client", client_factory)
    previous_logging = logging.root.manager.disable
    assert verify_nhl.main() == 0
    assert logging.root.manager.disable == previous_logging
    assert len(calls) == 6
    assert all(response.is_closed for response in closed)
    captured = capsys.readouterr()
    assert "Invented Ice League" in captured.out  # Visible only inside private buffer.
    summary = captured.out.split("\x1b[?1049l")[-1]
    assert len(summary.splitlines()) == len(Check)
    assert all(
        line.split()[0] in {check.value for check in Check} and line.endswith(" PASS")
        for line in summary.splitlines()
    )
    for private in ("Invented", "999.l.", "2099", "0.123456", "fake-verifier", state):
        assert private not in summary
    assert not captured.err and not caplog.records


def test_ai_flag_prevents_authorization_even_after_human_approval(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    from fantasy_gm import verify_nhl

    @contextmanager
    def terminal() -> Iterator[None]:
        yield

    def forbidden(*args: object) -> Never:
        raise AssertionError("Authentication is not allowed")

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    monkeypatch.setenv("YAHOO_AI_TOOLS_ENABLED", "true")
    monkeypatch.setattr(verify_nhl, "_private_terminal", terminal)
    monkeypatch.setattr(
        verify_nhl, "_read_hidden_input", lambda prompt: "APPROVE PRIVATE READ-ONLY"
    )
    monkeypatch.setattr(verify_nhl, "_authorize", forbidden)
    assert verify_nhl.main() == 1
    output = capsys.readouterr().out
    assert "LIVE_APPROVAL FAIL" in output
    assert "AUTHORIZATION UNVERIFIED" in output


def test_redirected_session_cannot_authenticate() -> None:
    result = subprocess.run(
        [sys.executable, "-B", "-m", "fantasy_gm.verify_nhl", "--interactive"],
        input="APPROVE PRIVATE READ-ONLY\n",
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 1
    assert "PRIVATE_TERMINAL FAIL" in result.stdout.splitlines()
    assert not result.stderr
