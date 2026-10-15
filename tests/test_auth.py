"""Exercise the human CLI pipeline with fake input and synthetic HTTP only."""

import getpass
import logging
import sys
import warnings
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

import httpx
import pytest

from fantasy_gm import auth
from fantasy_gm.auth import main, run_authorization
from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.providers.yahoo.fantasy import LEAGUE_DISCOVERY_URL
from fantasy_gm.providers.yahoo.oauth import TOKEN_ENDPOINT, YahooOAuthError
from fantasy_gm.providers.yahoo.session import YahooAuthorizationSessionError
from tests.test_yahoo_fantasy import SYNTHETIC_XML


def test_complete_manual_pipeline_does_not_persist(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.chdir(tmp_path)
    output: list[str] = []
    calls: list[httpx.Request] = []

    def read_secret(prompt: str) -> str:
        if prompt == "Authorization code: ":
            return "fake-code-for-tests"
        return parse_qs(urlsplit(output[1]).query)["state"][0]

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
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

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        run_authorization(
            YahooOAuthConfig(client_id="fake-client-id"),
            client,
            read_secret=read_secret,
            display=output.append,
        )
    assert len(calls) == 2
    rendered = "\n".join(output)
    assert "Synthetic Hockey One" in rendered and "999.l.1001" in rendered
    assert "data provided by Yahoo" in rendered
    for secret in (
        "fake-access-token",
        "fake-refresh-token",
        "fake-code-for-tests",
        "code_verifier",
    ):
        assert secret not in rendered
    assert list(tmp_path.iterdir()) == []


def test_wrong_state_pipeline_makes_no_http() -> None:
    with httpx.Client() as client:
        with pytest.raises(YahooAuthorizationSessionError):
            run_authorization(
                YahooOAuthConfig(client_id="fake-id"),
                client,
                read_secret=lambda prompt: "fake-invalid-state",
                display=lambda value: None,
            )


def test_unsupported_token_type_never_calls_discovery() -> None:
    output: list[str] = []
    calls: list[httpx.Request] = []

    def read_secret(prompt: str) -> str:
        if prompt == "Authorization code: ":
            return "fake-code-for-tests"
        return parse_qs(urlsplit(output[1]).query)["state"][0]

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        assert str(request.url) == TOKEN_ENDPOINT
        return httpx.Response(
            200,
            json={
                "access_token": "fake-access-token",
                "expires_in": 3600,
                "token_type": "fake-unsupported-type",
            },
        )

    with httpx.Client(transport=httpx.MockTransport(handle)) as client:
        with pytest.raises(YahooOAuthError, match="Unsupported"):
            run_authorization(
                YahooOAuthConfig(client_id="fake-id"),
                client,
                read_secret=read_secret,
                display=output.append,
            )
    assert len(calls) == 1


def test_hidden_input_unavailable_never_calls_http() -> None:
    def unavailable(prompt: str) -> str:
        raise getpass.GetPassWarning("fake-no-hidden-input")

    with httpx.Client() as client:
        with pytest.raises(getpass.GetPassWarning):
            run_authorization(
                YahooOAuthConfig(client_id="fake-id"),
                client,
                read_secret=unavailable,
                display=lambda value: None,
            )


def test_cli_rejects_redirected_output(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth"])
    assert main() == 2
    assert "interactive terminal" in capsys.readouterr().err


def test_cli_rejects_secret_command_line_arguments(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth", "fake-code-for-tests"])
    assert main() == 2
    output = capsys.readouterr()
    assert "fake-code-for-tests" not in output.out + output.err


def test_cli_help_makes_no_http(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth", "--help"])
    assert main() == 0
    assert "interactive terminal" in capsys.readouterr().out


@pytest.fixture
def interactive_cli(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["fantasy_gm.auth"])
    monkeypatch.setenv("YAHOO_CLIENT_ID", "fake-client-id-for-tests")


@pytest.mark.parametrize(
    "failure,expected_calls",
    [
        ("cancel-code", 0),
        ("cancel-state", 0),
        ("eof", 0),
        ("hidden-warning", 0),
        ("invalid-state", 0),
        ("token-rejected", 1),
        ("malformed-token", 1),
        ("invalid-access-token", 1),
        ("fantasy-rejected", 2),
    ],
)
def test_main_sanitizes_failure_and_restores_logging(
    interactive_cli: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failure: str,
    expected_calls: int,
) -> None:
    # Patch during the call phase, after pytest installs its output capture.
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    output: list[str] = []
    calls: list[httpx.Request] = []
    original_client = httpx.Client
    original_run = run_authorization
    previous_logging = logging.root.manager.disable

    def read_secret(prompt: str) -> str:
        if failure == "cancel-code" or (
            failure == "cancel-state" and prompt == "Returned state: "
        ):
            raise KeyboardInterrupt
        if failure == "eof":
            raise EOFError("fake-sensitive-code")
        if failure == "hidden-warning":
            warnings.warn("fake-sensitive-code", getpass.GetPassWarning, stacklevel=2)
            pytest.fail("Hidden-input warning must prevent any echoing fallback")
        if prompt == "Authorization code: ":
            return "fake-sensitive-code"
        if failure == "invalid-state":
            return "fake-wrong-state"
        return parse_qs(urlsplit(output[1]).query)["state"][0]

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if str(request.url) == TOKEN_ENDPOINT:
            if failure == "token-rejected":
                return httpx.Response(
                    400, json={"error_description": "fake-sensitive-code"}
                )
            if failure == "malformed-token":
                return httpx.Response(
                    200, json={"access_token": "fake-sensitive-access"}
                )
            return httpx.Response(
                200,
                json={
                    "access_token": (
                        "fake-sensitive-\u2603-access"
                        if failure == "invalid-access-token"
                        else "fake-sensitive-access"
                    ),
                    "refresh_token": "fake-sensitive-refresh",
                    "expires_in": 3600,
                    "token_type": "bearer",
                },
            )
        assert str(request.url) == LEAGUE_DISCOVERY_URL
        return httpx.Response(403, stream=httpx.ByteStream(b"fake-sensitive-league"))

    def client_factory(*, trust_env: bool) -> httpx.Client:
        assert trust_env is False
        return original_client(transport=httpx.MockTransport(handle), trust_env=False)

    def injected_run(config: YahooOAuthConfig, client: httpx.Client) -> None:
        assert logging.root.manager.disable == logging.CRITICAL
        original_run(config, client, read_secret=read_secret, display=output.append)

    monkeypatch.setattr(httpx, "Client", client_factory)
    monkeypatch.setattr(auth, "run_authorization", injected_run)
    assert main() == 1
    assert logging.root.manager.disable == previous_logging
    assert len(calls) == expected_calls
    captured = capsys.readouterr()
    assert captured.err and "Traceback" not in captured.err
    rendered = captured.err + captured.out + "\n".join(output)
    assert "fake-sensitive" not in rendered


def test_main_missing_configuration_is_clear(
    interactive_cli: None,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.delenv("YAHOO_CLIENT_ID")
    previous_logging = logging.root.manager.disable
    assert main() == 2
    assert "YAHOO_CLIENT_ID" in capsys.readouterr().err
    assert logging.root.manager.disable == previous_logging
