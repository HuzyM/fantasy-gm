"""The integrated private application uses synthetic HTTP and fake authorization."""

import builtins
import io
import logging
import sys
from collections.abc import Iterator
from contextlib import contextmanager

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm import league as cli
from fantasy_gm import verify_nhl
from tests.test_yahoo_contract_verifier import (
    DISCOVERY,
    OWNED,
    ROSTER,
    SETTINGS,
    TEAM,
    TEAMS,
)


def install_session(
    monkeypatch: pytest.MonkeyPatch,
    payloads: list[bytes],
    *,
    cancel_team: bool = False,
    reject_at: int | None = None,
) -> list[httpx.Request]:
    calls: list[httpx.Request] = []
    real_client = httpx.Client

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        logging.critical("private-library-log")
        return httpx.Response(
            401 if len(calls) == reject_at else 200,
            stream=httpx.ByteStream(payloads[len(calls) - 1]),
        )

    def client(*, transport: httpx.BaseTransport, trust_env: bool) -> httpx.Client:
        assert trust_env is False
        transport.close()
        return real_client(transport=httpx.MockTransport(handle), trust_env=False)

    @contextmanager
    def modes() -> Iterator[None]:
        yield

    selections = 0

    def answer(prompt: str) -> str:
        nonlocal selections
        if "attest and approve" in prompt:
            return "APPROVE PRIVATE READ-ONLY"
        if "Selection number" in prompt:
            selections += 1
            return "CANCEL" if cancel_team and selections == 2 else "1"
        return "NEXT"

    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(sys, "argv", ["league", "--interactive"])
    monkeypatch.setattr(verify_nhl, "_terminal_modes", modes)
    monkeypatch.setattr(verify_nhl, "_read_hidden_input", answer)
    monkeypatch.setattr(cli, "_read_hidden_input", answer)
    monkeypatch.setattr(
        cli, "_authorize", lambda client: SecretStr("fake-private-token")
    )
    monkeypatch.setattr(httpx, "Client", client)
    return calls


@pytest.mark.parametrize(
    "scenario",
    [
        "supported",
        "unknown_scoring",
        "unknown_roster",
        "reported_state",
        "combined_partial",
    ],
)
def test_private_application_keeps_independent_features_and_a_fixed_public_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    scenario: str,
) -> None:
    payloads = [DISCOVERY, OWNED, TEAMS, SETTINGS, ROSTER]
    if scenario == "unknown_scoring":
        payloads[3] = SETTINGS.replace(
            b"</settings>",
            b"<synthetic_bonus>private-value</synthetic_bonus></settings>",
        )
    elif scenario == "unknown_roster":
        payloads[4] = ROSTER.replace(b"<roster>", b'<roster synthetic="private-value">')
    elif scenario == "reported_state":
        payloads[4] = ROSTER.replace(
            b"</roster>", b"<is_prescoring>0</is_prescoring></roster>"
        )
    elif scenario == "combined_partial":
        payloads[3] = SETTINGS.replace(
            b"</settings>",
            b"<synthetic_bonus>private-value</synthetic_bonus></settings>",
        ).replace(
            b"<roster_positions>", b'<roster_positions synthetic="private-value">'
        )
        payloads[4] = ROSTER.replace(b"<date>2099-10-15</date>", b"<date/>", 1)
    calls = install_session(monkeypatch, payloads)

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected filesystem access")

    previous_logging = logging.root.manager.disable
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        code = cli.main()
    captured = capsys.readouterr()
    private, public = captured.out.split(verify_nhl._LEAVE_PRIVATE)
    assert (
        public
        == f"PRIVATE_SESSION {'FINISHED' if scenario == 'supported' else 'PARTIAL'}\n"
    )
    assert code == (0 if scenario == "supported" else 1)
    assert len(calls) == 5 and all(request.method == "GET" for request in calls)
    assert [r.url.path.rsplit("/", 1)[-1] for r in calls] == [
        "leagues",
        "teams",
        "teams",
        "settings",
        "roster",
    ]
    assert "Invented Ice Team" in private and "private-value" not in captured.out
    assert "0.12345678901234567890123456789" in private and "-2.50" in private
    assert "Invented Skater" in private and "IR+" in private
    warning = "Completeness, lineup legality and capacity are UNVERIFIED"
    assert warning in " ".join(private.split())
    if scenario in ("unknown_scoring", "combined_partial"):
        assert "Partial scoring observations" in private
        assert "not calculation-ready" in private
    if scenario in ("unknown_roster", "reported_state", "combined_partial"):
        assert "Some roster metadata or optional fields are unresolved" in private
    if scenario == "combined_partial":
        assert "Partial roster-slot observations" in private
        assert "Reported date: not supplied / unknown" in private
    assert not caplog.records and not captured.err
    assert logging.root.manager.disable == previous_logging


@pytest.mark.parametrize(
    "stage",
    [
        "membership",
        "settings_identity",
        "roster_identity",
        "transport",
        "private_display",
        "cancel",
    ],
)
def test_real_prerequisite_and_private_interface_failures_stop_dependent_requests(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    stage: str,
) -> None:
    payloads = [DISCOVERY, OWNED, TEAMS, SETTINGS, ROSTER]
    expected = {
        "membership": 3,
        "settings_identity": 4,
        "roster_identity": 5,
        "transport": 4,
        "private_display": 4,
        "cancel": 3,
    }[stage]
    if stage == "membership":
        payloads[2] = TEAMS.replace(b"999.l.1001.t.1", b"999.l.1001.t.2")
    elif stage == "settings_identity":
        payloads[3] = SETTINGS.replace(b"999.l.1001", b"999.l.1002")
    elif stage == "roster_identity":
        payloads[4] = ROSTER.replace(b"999.l.1001.t.1", b"999.l.1001.t.2")
    calls = install_session(
        monkeypatch,
        payloads,
        cancel_team=stage == "cancel",
        reject_at=4 if stage == "transport" else None,
    )
    if stage == "private_display":

        def fail(details: tuple[str, ...]) -> None:
            raise ValueError("private-failure")

        monkeypatch.setattr(cli, "_show", fail)
    assert cli.main() == 1
    captured = capsys.readouterr()
    assert len(calls) == expected
    assert (
        captured.out.split(verify_nhl._LEAVE_PRIVATE)[-1]
        == f"PRIVATE_SESSION {'CANCELLED' if stage == 'cancel' else 'FAILED'}\n"
    )
    assert "private-failure" not in captured.out and not captured.err


def test_callback_selects_only_owned_teams_without_rereads() -> None:
    from fantasy_gm.providers.yahoo.fantasy import YahooFantasyClient, YahooFantasyError

    second = (
        TEAM.replace("999.l.1001.t.1", "999.l.1001.t.2")
        .replace("<team_id>1", "<team_id>2")
        .replace("Invented Ice Team", "Invented Second Team")
        .encode()
    )
    owned = OWNED.replace(b'count="1"><team>', b'count="2"><team>').replace(
        b"</teams>", second + b"</teams>"
    )
    teams = TEAMS.replace(b'count="1"><team>', b'count="2"><team>').replace(
        b"</teams>", second + b"</teams>"
    )
    roster = ROSTER.replace(b"999.l.1001.t.1", b"999.l.1001.t.2")
    for selected, expected in (("999.l.1001.t.2", 3), ("999.l.1001.t.999", 2)):
        calls: list[httpx.Request] = []

        def handle(
            request: httpx.Request, calls: list[httpx.Request] = calls
        ) -> httpx.Response:
            calls.append(request)
            return httpx.Response(
                200, stream=httpx.ByteStream([owned, teams, roster][len(calls) - 1])
            )

        def choose(owned: tuple[object, ...], selected: str = selected) -> str:
            assert len(owned) == 2
            return selected

        with httpx.Client(
            transport=httpx.MockTransport(handle), trust_env=False
        ) as client:
            provider = YahooFantasyClient(http_client=client)
            if expected == 3:
                result = provider.get_owned_team_roster(
                    SecretStr("fake-token"), league_key="999.l.1001", choose_team=choose
                )
                assert result.team.provider_team_id == selected
            else:
                with pytest.raises(YahooFantasyError):
                    provider.get_owned_team_roster(
                        SecretStr("fake-token"),
                        league_key="999.l.1001",
                        choose_team=choose,
                    )
        assert len(calls) == expected


def test_ai_flag_and_redirected_terminal_fail_before_authorization(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls = install_session(monkeypatch, [])
    authorization_attempts: list[bool] = []

    def deny(client: httpx.Client) -> None:
        authorization_attempts.append(True)
        raise AssertionError("Authorization must not be called")

    monkeypatch.setattr(cli, "_authorize", deny)
    monkeypatch.setenv("YAHOO_AI_TOOLS_ENABLED", "true")
    assert cli.main() == 1 and not calls
    assert not authorization_attempts
    assert capsys.readouterr().out.endswith("PRIVATE_SESSION FAILED\n")
    monkeypatch.setattr(sys.stdout, "isatty", lambda: False)
    assert cli.main() == 1 and not calls
    assert not authorization_attempts
    assert capsys.readouterr().out == "PRIVATE_SESSION FAILED\n"


@pytest.mark.parametrize("kind", ["other_sport", "duplicate"])
def test_ambiguous_or_non_nhl_discovery_stops_before_team_requests(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    kind: str,
) -> None:
    body = DISCOVERY.replace(b"<game_code>nhl", b"<game_code>mlb")
    if kind == "duplicate":
        start = DISCOVERY.index(b"<league>")
        end = DISCOVERY.index(b"</league>") + len(b"</league>")
        body = DISCOVERY.replace(
            b'<leagues count="1">', b'<leagues count="2">'
        ).replace(b"</leagues>", DISCOVERY[start:end] + b"</leagues>")
    calls = install_session(monkeypatch, [body])
    assert cli.main() == 1 and len(calls) == 1
    assert capsys.readouterr().out.endswith("PRIVATE_SESSION FAILED\n")


def test_terminal_cleanup_failure_overrides_success(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    @contextmanager
    def terminal() -> Iterator[None]:
        yield
        raise ValueError("private-cleanup-failure")

    monkeypatch.setattr(sys, "argv", ["league", "--interactive"])
    monkeypatch.setattr(cli, "_private_terminal", terminal)
    monkeypatch.setattr(cli, "_run_private", lambda: True)
    assert cli.main() == 1
    captured = capsys.readouterr()
    assert captured.out == "PRIVATE_SESSION FAILED\n" and not captured.err
