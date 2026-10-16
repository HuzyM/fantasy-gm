"""Visible navigation stays separate from hidden OAuth input; synthetic only."""

import builtins
import getpass
from datetime import date

import httpx
import pytest

from fantasy_gm import auth, verify_nhl
from fantasy_gm import roster_schedule as cli
from fantasy_gm.providers.yahoo.contract_verifier import SelectionCancelled


def test_ordinary_input_uses_visible_terminal_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(builtins, "input", lambda prompt: "  NEXT  ")
    monkeypatch.setattr(getpass, "getpass", lambda _: pytest.fail("Must be visible"))
    assert auth._read_visible_input("Navigation: ") == "NEXT"


def test_selection_retries_invalid_values_without_echoing_them(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(["NEXT", "", "invented-sensitive-value", "0", "99", "1"])
    assert (
        verify_nhl._choose(
            "Select", ("First", "Second"), read_input=lambda _: next(answers)
        )
        == 0
    )
    output = capsys.readouterr().out
    assert "Invalid selection" in output
    assert "invented-sensitive-value" not in output


def test_pagination_retries_and_goes_back_to_previous_page(
    capsys: pytest.CaptureFixture[str],
) -> None:
    answers = iter(["typo", "NEXT", "BACK", "NEXT", "NEXT", "NEXT"])
    verify_nhl._show(
        tuple(f"Row {i}" for i in range(25)), read_input=lambda _: next(answers)
    )
    output = capsys.readouterr().out
    assert output.count("Row 0\n") == 2
    assert "Row 24" in output and "NEXT" in output


@pytest.mark.parametrize("action", ["CANCEL", "BACK"])
def test_selection_explicit_navigation(action: str) -> None:
    expected = SelectionCancelled if action == "CANCEL" else verify_nhl._BackRequested
    with pytest.raises(expected):
        verify_nhl._choose(
            "Select", ("First",), read_input=lambda _: action, allow_back=True
        )


def test_initial_selection_back_retries_without_restarting() -> None:
    answers = iter(["NEXT", "BACK", "1"])
    assert (
        verify_nhl._choose("Select", ("First",), read_input=lambda _: next(answers))
        == 0
    )


def test_confirmation_typo_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    answers = iter(["NEX", "", "NEXT"])
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    cli._next()


@pytest.mark.parametrize("action", ["CANCEL", "BACK"])
def test_confirmation_explicit_navigation(
    monkeypatch: pytest.MonkeyPatch, action: str
) -> None:
    monkeypatch.setattr(builtins, "input", lambda _: action)
    expected = SelectionCancelled if action == "CANCEL" else verify_nhl._BackRequested
    with pytest.raises(expected):
        cli._next()


def test_dates_retry_invalid_input_and_back_edits_start(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    answers = iter(
        [
            "not-a-date",
            "2025-10-01",
            "2026-10-20",
            "BACK",
            "2026-10-21",
            "bad",
            "2026-10-20",
            "2026-12-01",
            "2026-10-23",
        ]
    )
    monkeypatch.setattr(builtins, "input", lambda _: next(answers))
    assert cli._window(2026) == (date(2026, 10, 21), date(2026, 10, 23))
    assert "Invalid" in capsys.readouterr().out


@pytest.mark.parametrize("answers", [("CANCEL",), ("2026-10-20", "CANCEL")])
def test_dates_cancel_at_either_prompt(
    monkeypatch: pytest.MonkeyPatch, answers: tuple[str, ...]
) -> None:
    values = iter(answers)
    monkeypatch.setattr(builtins, "input", lambda _: next(values))
    with pytest.raises(SelectionCancelled):
        cli._window(2026)


def test_oauth_keeps_sensitive_inputs_hidden_and_wrong_state_fails_before_http(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    from fantasy_gm.providers.yahoo.session import YahooAuthorizationSessionError

    monkeypatch.setenv("YAHOO_CLIENT_ID", "synthetic-client")
    secrets = iter(["synthetic-code", "synthetic-wrong-state"])
    monkeypatch.setattr(getpass, "getpass", lambda _: next(secrets))
    monkeypatch.setattr(builtins, "input", lambda _: pytest.fail("Secret was visible"))
    with httpx.Client(
        transport=httpx.MockTransport(lambda _: pytest.fail("No HTTP"))
    ) as client:
        with pytest.raises(YahooAuthorizationSessionError):
            verify_nhl._authorize(client)
    output = capsys.readouterr().out
    assert "synthetic-code" not in output and "synthetic-wrong-state" not in output
