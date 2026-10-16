"""Human-only private NHL contract verifier. Never run through an AI terminal."""

import logging
import os
import sys
import warnings
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from textwrap import wrap

import httpx
from pydantic import SecretStr

from fantasy_gm.auth import _read_hidden_input
from fantasy_gm.config.yahoo import YahooOAuthConfig
from fantasy_gm.providers.yahoo.contract_verifier import (
    Check,
    Report,
    SelectionCancelled,
    Status,
    StopReason,
    verify_contracts,
)
from fantasy_gm.providers.yahoo.oauth import YahooOAuthClient
from fantasy_gm.providers.yahoo.session import YahooAuthorizationSession

_ENTER_PRIVATE = "\x1b[?1049h\x1b[2J\x1b[H"
_CLEAR_PRIVATE = "\x1b[2J\x1b[H"
_LEAVE_PRIVATE = "\x1b[2J\x1b[H\x1b[?1049l"
_APPROVAL = "APPROVE PRIVATE READ-ONLY"
_QUESTIONS = {
    Check.HUMAN_POINTS_FORMAT: (
        "Confirm this is your NHL head-to-head POINTS league on Yahoo's website. "
        "The displayed code is opaque; no universal scoring-code mapping is assumed."
    ),
    Check.HUMAN_SCORING_COMPLETE: (
        "Compare EVERY scoring component with Yahoo's settings. Confirm all weights "
        "match exactly, including negatives and zero. Every missing weight must be "
        "explained as unscored/display-only. Reject missing labels or bonuses, "
        "thresholds, "
        "or rules that this view does not fully represent. No points are calculated."
    ),
    Check.HUMAN_POSITION_SCOPES: (
        "Compare the statistic position scopes and display-only flags with Yahoo. "
        "Confirm their applicability is unambiguous, including skaters and goalies. "
        "UNKNOWN if the website cannot establish the meaning of these flags."
    ),
    Check.HUMAN_ROSTER_SLOTS: (
        "Confirm all configured roster slots and capacities match Yahoo, including "
        "bench and reserve positions. No position codes are translated."
    ),
    Check.HUMAN_LEAGUE_TEAMS_COMPLETE: (
        "Confirm this is the complete team list for your selected league on Yahoo."
    ),
    Check.HUMAN_PLAYER_POSITIONS: (
        "Compare EVERY player, eligibility list, and assigned position with Yahoo's "
        "roster for the reported coverage. Confirm all match."
    ),
    Check.HUMAN_ROSTER_COVERAGE: (
        "Confirm the reported roster and selected-position dates match the date "
        "you are viewing on Yahoo. Missing dates remain UNVERIFIED regardless of "
        "your answer. UNKNOWN if coverage or season behavior cannot be established."
    ),
    Check.HUMAN_ROSTER_COMPLETE: (
        "Confirm EVERY roster member is present, including all bench and reserve "
        "slots. Empty configured slots are allowed. Check for omitted pages or "
        "truncation; a returned count alone is not completeness proof."
    ),
}


@contextmanager
def _terminal_modes() -> Iterator[None]:
    """Require VT alternate-screen support; restore original Windows modes."""
    if os.name != "nt":
        if not os.environ.get("TERM", "").startswith(("xterm", "screen", "tmux")):
            raise ValueError()
        yield
        return
    import ctypes
    from ctypes import wintypes

    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetStdHandle.argtypes = [wintypes.DWORD]
    kernel.GetStdHandle.restype = wintypes.HANDLE
    kernel.GetConsoleMode.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
    kernel.SetConsoleMode.argtypes = [wintypes.HANDLE, wintypes.DWORD]
    modes: list[tuple[int, int]] = []
    try:
        for identifier in (-11, -12):  # stdout and stderr must both be consoles.
            handle = kernel.GetStdHandle(identifier & 0xFFFFFFFF)
            mode = wintypes.DWORD()
            if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
                raise ValueError()
            modes.append((handle, mode.value))
            if not kernel.SetConsoleMode(handle, mode.value | 0x0004):
                raise ValueError()
        yield
    finally:
        for handle, mode_value in reversed(modes):
            kernel.SetConsoleMode(handle, mode_value)


@contextmanager
def _private_terminal() -> Iterator[None]:
    if not all(stream.isatty() for stream in (sys.stdin, sys.stdout, sys.stderr)):
        raise ValueError()
    with _terminal_modes():
        try:
            sys.stdout.write(_ENTER_PRIVATE)
            sys.stdout.flush()
            yield
        finally:
            sys.stdout.write(_LEAVE_PRIVATE)
            sys.stdout.flush()


class _BackRequested(Exception):
    """Return to the preceding private view without cancelling the session."""


def _show(
    lines: tuple[str, ...],
    *,
    read_input: Callable[[str], str] | None = None,
    allow_back: bool = False,
) -> None:
    """Only already-escaped private fields, paginated within the alternate screen."""
    rows = [part for line in lines for part in (wrap(line, width=72) or [""])]
    start = 0
    while start < len(rows):
        sys.stdout.write(_CLEAR_PRIVATE)
        print("Yahoo Fantasy Sports — data provided by Yahoo. PRIVATE; do not share.")
        print("\n".join(rows[start : start + 12]))
        next_start = start + 12
        if read_input is not None or start + 12 < len(rows):
            if read_input is None:
                if _read_hidden_input("Type NEXT to continue, or CANCEL: ") != "NEXT":
                    raise KeyboardInterrupt()
            else:
                while True:
                    action = read_input("Type NEXT, BACK, or CANCEL: ").upper()
                    if action == "CANCEL":
                        raise SelectionCancelled()
                    if action == "NEXT":
                        break
                    if action == "BACK":
                        if start:
                            next_start = start - 12
                            break
                        if allow_back:
                            raise _BackRequested()
                        print("Already on the first page. Type NEXT or CANCEL.")
                    else:
                        print("Invalid action. Type NEXT, BACK, or CANCEL.")
        start = next_start


def _choose(
    title: str,
    options: tuple[str, ...],
    *,
    read_input: Callable[[str], str] | None = None,
    allow_back: bool = False,
) -> int | None:
    lines = (title,) + tuple(f"{i + 1}: {row}" for i, row in enumerate(options))
    if read_input is None:
        _show(lines)
    else:
        _show(lines, read_input=read_input, allow_back=allow_back)
        if not options:
            return None
    while True:
        value = (read_input or _read_hidden_input)(
            "Selection number, BACK, or CANCEL: "
            if read_input is not None
            else "Selection number, or CANCEL: "
        )
        action = value.upper() if read_input is not None else value
        if action == "CANCEL":
            raise SelectionCancelled()
        if read_input is not None and action == "BACK":
            if allow_back:
                raise _BackRequested()
            print("No earlier selection is available here. Select a number or CANCEL.")
            continue
        if value.isascii() and value.isdecimal() and len(value) <= 6:
            index = int(value) - 1
            if 0 <= index < len(options):
                return index
        if read_input is None:
            return None
        print(f"Invalid selection. Enter a number from 1 to {len(options)}, or CANCEL.")


def _confirm(check: Check, details: tuple[str, ...]) -> Status:
    _show(details)
    print(_QUESTIONS[check])
    value = _read_hidden_input("Type CONFIRM, REJECT, or UNKNOWN: ")
    return {"CONFIRM": Status.PASS, "REJECT": Status.FAIL}.get(value, Status.UNVERIFIED)


def _inspect_unsupported(details: tuple[str, ...]) -> None:
    """Private alternate-screen inspection only; never retained in Report."""
    try:
        _show(
            (
                "Unsupported structure does not mean Yahoo data is invalid.",
                "NEXT acknowledges this view; it does not approve any meaning.",
                "UNKNOWN is valid. Checks stay UNVERIFIED. Keep all details private.",
                "Names/shapes only; up to four mismatches. Names/lists are bounded.",
            )
            + details
        )
        if _read_hidden_input("Type NEXT or UNKNOWN to continue, or CANCEL: ") not in {
            "NEXT",
            "UNKNOWN",
        }:
            raise KeyboardInterrupt()
    except Exception:
        # A display/input ValueError must not look like scoring validation and
        # allow independent requests to continue after the private view failed.
        raise RuntimeError("Private structural inspection unavailable") from None


def _authorize(http_client: httpx.Client) -> SecretStr:
    oauth = YahooOAuthClient(
        YahooOAuthConfig.from_environment(), http_client=http_client
    )
    session = YahooAuthorizationSession()
    print("Open the following URL yourself in your private browser:")
    print(oauth.authorization_url(session))
    code = SecretStr(_read_hidden_input("Authorization code (hidden): "))
    state = _read_hidden_input("Returned state (hidden): ")
    tokens = oauth.exchange_code(code, session=session, returned_state=state)
    if tokens.token_type.casefold() != "bearer":
        raise ValueError()
    return tokens.access_token


def _run_private(report: Report) -> None:
    report.enter(Check.LIVE_APPROVAL)
    print(
        "Private human-operated verification only. Close AI/remote terminal views. "
        "Disable transcripts, recording, debugging, and screen sharing. No recording "
        "can be detected or undone by this utility. Do not proceed if any is active.\n"
        "Approval authorizes one OAuth exchange, league discovery, settings, owned "
        "teams, league teams, and one current roster. No refresh, retries, or writes."
    )
    if _read_hidden_input(f"Type {_APPROVAL} to attest and approve: ") != _APPROVAL:
        report.stop(Check.LIVE_APPROVAL, StopReason.HUMAN_CONFIRMATION_NOT_COMPLETED)
        return
    if os.environ.get("YAHOO_AI_TOOLS_ENABLED", "false") != "false":
        report.mark(Check.LIVE_APPROVAL, Status.FAIL)
        report.stop(Check.LIVE_APPROVAL, StopReason.VALIDATION_FAILED)
        return
    report.mark(Check.LIVE_APPROVAL, Status.PASS)
    # No inherited auth, event hooks, proxies, cache transports, or automatic retry.
    with httpx.Client(
        transport=httpx.HTTPTransport(retries=0, trust_env=False), trust_env=False
    ) as client:
        report.mark(Check.AUTHORIZATION, Status.FAIL)
        report.enter(Check.AUTHORIZATION)
        token = _authorize(client)
        report.mark(Check.AUTHORIZATION, Status.PASS)
        verify_contracts(
            token,
            http_client=client,
            report=report,
            choose=_choose,
            confirm=_confirm,
            inspect_unsupported=_inspect_unsupported,
        )
        report.enter(Check.SESSION)


def main() -> int:
    if sys.argv[1:] == ["--help"]:
        print(
            "Usage: python -B -m fantasy_gm.verify_nhl --interactive\n"
            "Use a private, unrecorded human terminal after separate approval.\n"
            "Share only the final check statuses and fixed diagnostic lines."
        )
        return 0
    report = Report()
    previous_logging = logging.root.manager.disable
    logging.disable(logging.CRITICAL)
    try:
        if sys.argv[1:] != ["--interactive"]:
            raise ValueError()
        report.mark(Check.PRIVATE_TERMINAL, Status.FAIL)
        report.enter(Check.PRIVATE_TERMINAL)
        with warnings.catch_warnings(), _private_terminal():
            # Fail closed if hidden input or any library emits a warning.
            warnings.simplefilter("error")
            report.mark(Check.PRIVATE_TERMINAL, Status.PASS)
            _run_private(report)
            report.enter(Check.SESSION)
    except KeyboardInterrupt:
        report.stop(
            report.active_check,
            StopReason.INTERACTION_INTERRUPTED,
            skipped=report.active_check
            not in (Check.SESSION, Check.HUMAN_ROSTER_COMPLETE),
        )
        report.mark(Check.SESSION, Status.FAIL)
    except Exception:
        # No messages, tracebacks, HTTP statuses, URLs, or validation inputs.
        report.mark(Check.SESSION, Status.FAIL)
        report.stop(
            report.active_check,
            StopReason.SESSION_ERROR,
            skipped=report.active_check
            not in (Check.SESSION, Check.HUMAN_ROSTER_COMPLETE),
        )
    finally:
        logging.disable(previous_logging)
    complete = not report.failed() and all(
        report.passed(check) for check in Check if check is not Check.SESSION
    )
    if complete:
        report.mark(Check.SESSION, Status.PASS)
    elif report.failed():
        report.mark(Check.SESSION, Status.FAIL)
    if not complete and not report.diagnostics():
        report.stop(Check.SESSION, StopReason.VALIDATION_INCOMPLETE, skipped=False)
    for line in report.lines() + report.diagnostics():
        print(line)
    return 0 if complete else 1


if __name__ == "__main__":
    raise SystemExit(main())
