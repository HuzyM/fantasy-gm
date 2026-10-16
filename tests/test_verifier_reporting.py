"""Allowlisted stop diagnostics, using invented fixtures and mocked HTTP only."""

import sys
from collections.abc import Callable, Iterator
from contextlib import contextmanager

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm import verify_nhl as cli
from fantasy_gm.providers.yahoo.contract_verifier import (
    Check,
    Report,
    Status,
    verify_contracts,
)
from tests.test_yahoo_contract_verifier import PAYLOADS, SETTINGS

ORIGINAL_STATUSES = """PRIVATE_TERMINAL PASS
LIVE_APPROVAL PASS
AUTHORIZATION PASS
LEAGUE_DISCOVERY PASS
SETTINGS_STRUCTURE PASS
SCORING_STRUCTURE UNVERIFIED
MODIFIER_VALUES UNVERIFIED
STAT_APPLICABILITY UNVERIFIED
ROSTER_SLOTS UNVERIFIED
HUMAN_POINTS_FORMAT UNVERIFIED
HUMAN_SCORING_COMPLETE UNVERIFIED
HUMAN_POSITION_SCOPES UNVERIFIED
HUMAN_ROSTER_SLOTS UNVERIFIED
OWNED_TEAM_MEMBERSHIP UNVERIFIED
LEAGUE_TEAMS_STRUCTURE UNVERIFIED
LEAGUE_TEAMS_COMPLETENESS UNVERIFIED
HUMAN_LEAGUE_TEAMS_COMPLETE UNVERIFIED
ROSTER_STRUCTURE UNVERIFIED
ROSTER_NORMALIZATION UNVERIFIED
PLAYER_POSITIONS UNVERIFIED
ROSTER_SLOT_CAPACITY UNVERIFIED
ROSTER_COVERAGE UNVERIFIED
ROSTER_RETURNED_COUNT UNVERIFIED
HUMAN_PLAYER_POSITIONS UNVERIFIED
HUMAN_ROSTER_COVERAGE UNVERIFIED
HUMAN_ROSTER_COMPLETE UNVERIFIED
SESSION UNVERIFIED""".splitlines()

# The former whole-session stop now skips only scoring-dependent checks.
SCORING_INCOMPLETE_STATUSES = [
    line.replace(" UNVERIFIED", " PASS")
    if line.split()[0]
    in {
        "ROSTER_SLOTS",
        "HUMAN_ROSTER_SLOTS",
        "OWNED_TEAM_MEMBERSHIP",
        "LEAGUE_TEAMS_STRUCTURE",
        "LEAGUE_TEAMS_COMPLETENESS",
        "HUMAN_LEAGUE_TEAMS_COMPLETE",
        "ROSTER_STRUCTURE",
        "ROSTER_NORMALIZATION",
        "PLAYER_POSITIONS",
        "ROSTER_SLOT_CAPACITY",
        "ROSTER_COVERAGE",
        "ROSTER_RETURNED_COUNT",
        "HUMAN_PLAYER_POSITIONS",
        "HUMAN_ROSTER_COVERAGE",
        "HUMAN_ROSTER_COMPLETE",
    }
    else line
    for line in ORIGINAL_STATUSES
]


def run_cli(
    monkeypatch: pytest.MonkeyPatch,
    payloads: list[bytes],
    *,
    human: Status = Status.PASS,
    choose: Callable[[str, tuple[str, ...]], int | None] = lambda title, options: 0,
) -> tuple[int, list[httpx.Request], list[Check]]:
    calls: list[httpx.Request] = []
    confirmations: list[Check] = []

    @contextmanager
    def private_terminal() -> Iterator[None]:
        yield

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    def confirm(check: Check, details: tuple[str, ...]) -> Status:
        confirmations.append(check)
        return human

    def private_run(report: Report) -> None:
        # Simulate completed gates without reading configuration or authenticating.
        report.mark(Check.LIVE_APPROVAL, Status.PASS)
        report.mark(Check.AUTHORIZATION, Status.PASS)
        with httpx.Client(
            transport=httpx.MockTransport(handle), trust_env=False
        ) as client:
            verify_contracts(
                SecretStr("fake-report-token"),
                http_client=client,
                report=report,
                choose=choose,
                confirm=confirm,
            )

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    monkeypatch.setattr(cli, "_private_terminal", private_terminal)
    monkeypatch.setattr(cli, "_run_private", private_run)
    return cli.main(), calls, confirmations


@pytest.mark.parametrize(
    ("old", "new", "reason"),
    [
        (
            b"</settings>",
            b"<synthetic_trade_status/></settings>",
            "UNSUPPORTED_SCORING_SETTING",
        ),
        (
            b"<stat_categories>",
            b"<stat_categories><synthetic_extension/>",
            "UNSUPPORTED_SCORING_CONTAINER",
        ),
        (
            b"<stat_categories>",
            b"<stat_categories fake_metadata='private-sentinel'>",
            "UNSUPPORTED_SCORING_CONTAINER",
        ),
        (
            b"<name>Invented Goals</name>",
            b"<name>Invented Goals</name><synthetic_extension/>",
            "UNSUPPORTED_STAT_STRUCTURE",
        ),
        (
            b"<value>-2.50</value>",
            b"<value fake_unit='private-sentinel'>-2.50</value>",
            "UNSUPPORTED_MODIFIER_STRUCTURE",
        ),
    ],
)
def test_original_status_pattern_gets_precise_scoring_reason(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    old: bytes,
    new: bytes,
    reason: str,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(old, new)
    code, calls, confirmations = run_cli(monkeypatch, payloads)
    captured = capsys.readouterr()
    assert code == 1 and len(calls) == 5
    assert Check.HUMAN_SCORING_COMPLETE not in confirmations
    assert captured.out.splitlines() == SCORING_INCOMPLETE_STATUSES + [
        "STOP_CHECK SCORING_STRUCTURE",
        f"STOP_REASON {reason}",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]
    assert not captured.err
    assert not any(
        value in captured.out
        for value in (
            "private-sentinel",
            "999.l.",
            "Invented",
            "fake-report-token",
            "-2.50",
        )
    )


@pytest.mark.parametrize("container", ["stat_categories", "stat_modifiers"])
def test_empty_scoring_collection_has_its_own_reason(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    container: str,
) -> None:
    start = SETTINGS.index(f"<{container}>".encode())
    end = SETTINGS.index(f"</{container}>".encode()) + len(f"</{container}>")
    payloads = PAYLOADS.copy()
    payloads[1] = (
        SETTINGS[:start]
        + f"<{container}><stats/></{container}>".encode()
        + SETTINGS[end:]
    )
    code, calls, confirmations = run_cli(monkeypatch, payloads)
    assert code == 1 and len(calls) == 5
    assert Check.HUMAN_SCORING_COMPLETE not in confirmations
    assert capsys.readouterr().out.splitlines() == SCORING_INCOMPLETE_STATUSES + [
        "STOP_CHECK SCORING_STRUCTURE",
        "STOP_REASON EMPTY_SCORING_COLLECTION",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]


@pytest.mark.parametrize(
    ("old", "check"),
    [
        (b"<value>-2.50</value>", "MODIFIER_VALUES"),
        (b"<scoring_type>invented-points</scoring_type>", "SCORING_STRUCTURE"),
    ],
)
def test_missing_required_value_still_fails(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    old: bytes,
    check: str,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(old, b"")
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out.splitlines()
    assert code == 1 and len(calls) == 5
    assert f"{check} FAIL" in output and "SESSION FAIL" in output
    assert output[-3:] == [
        f"STOP_CHECK {check}",
        "STOP_REASON VALIDATION_FAILED",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]


@pytest.mark.parametrize(
    "human,reason",
    [
        (Status.UNVERIFIED, "HUMAN_CONFIRMATION_NOT_COMPLETED"),
        (Status.FAIL, "HUMAN_CONFIRMATION_REJECTED"),
    ],
)
def test_human_outcome_preserves_status_and_explains_stop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    human: Status,
    reason: str,
) -> None:
    code, calls, prompts = run_cli(monkeypatch, PAYLOADS, human=human)
    output = capsys.readouterr().out.splitlines()
    assert code == 1 and len(calls) == (4 if human is Status.UNVERIFIED else 2)
    assert prompts == [Check.HUMAN_POINTS_FORMAT] + (
        [Check.HUMAN_LEAGUE_TEAMS_COMPLETE] if human is Status.UNVERIFIED else []
    )
    assert f"HUMAN_POINTS_FORMAT {human.value}" in output
    ownership = "PASS" if human is Status.UNVERIFIED else "UNVERIFIED"
    assert f"OWNED_TEAM_MEMBERSHIP {ownership}" in output
    assert output[len(Check) : len(Check) + 3] == [
        "STOP_CHECK HUMAN_POINTS_FORMAT",
        f"STOP_REASON {reason}",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]
    if human is Status.UNVERIFIED:
        assert output[-3:] == [
            "LAST_STOP_CHECK HUMAN_LEAGUE_TEAMS_COMPLETE",
            f"LAST_STOP_REASON {reason}",
            "LAST_DOWNSTREAM_CHECKS_SKIPPED YES",
        ]


def test_success_has_no_stop_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    code, calls, _ = run_cli(monkeypatch, PAYLOADS)
    output = capsys.readouterr().out.splitlines()
    assert code == 0 and len(calls) == 5 and len(output) == len(Check)
    assert all(line.endswith(" PASS") for line in output)


def test_menu_cancellation_is_distinct_from_invalid_selection(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(cli, "_read_hidden_input", lambda prompt: "CANCEL")
    code, calls, _ = run_cli(monkeypatch, PAYLOADS, choose=cli._choose)
    output = capsys.readouterr().out.splitlines()
    assert code == 1 and len(calls) == 1
    assert "SESSION UNVERIFIED" in output
    assert output[-3:] == [
        "STOP_CHECK LEAGUE_DISCOVERY",
        "STOP_REASON USER_CANCELLED",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]

    code, calls, _ = run_cli(monkeypatch, PAYLOADS, choose=lambda title, options: None)
    output = capsys.readouterr().out.splitlines()
    assert code == 1 and len(calls) == 1
    assert output[-3:] == [
        "STOP_CHECK LEAGUE_DISCOVERY",
        "STOP_REASON SELECTION_NOT_COMPLETED",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]


def test_keyboard_interruption_keeps_failure_status_and_static_diagnostic(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def interrupt(title: str, options: tuple[str, ...]) -> int | None:
        raise KeyboardInterrupt()

    code, calls, _ = run_cli(monkeypatch, PAYLOADS, choose=interrupt)
    output = capsys.readouterr().out.splitlines()
    assert code == 1 and len(calls) == 1 and "SESSION FAIL" in output
    assert output[-3:] == [
        "STOP_CHECK LEAGUE_DISCOVERY",
        "STOP_REASON INTERACTION_INTERRUPTED",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]


def test_last_human_check_stops_without_claiming_downstream_skips() -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import _human, _Stop

    report = Report()
    with pytest.raises(_Stop):
        _human(
            report,
            Check.HUMAN_ROSTER_COMPLETE,
            (),
            lambda check, details: Status.UNVERIFIED,
        )
    assert not report.passed(Check.HUMAN_ROSTER_COMPLETE)
    assert report.diagnostics() == (
        "STOP_CHECK HUMAN_ROSTER_COMPLETE",
        "STOP_REASON HUMAN_CONFIRMATION_NOT_COMPLETED",
        "DOWNSTREAM_CHECKS_SKIPPED NO",
    )


def test_incomplete_coverage_at_end_is_not_an_early_stop(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    payloads = PAYLOADS.copy()
    payloads[4] = payloads[4].replace(b"<date>2099-10-15</date>", b"")
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out.splitlines()
    assert code == 1 and len(calls) == 5
    assert "SESSION UNVERIFIED" in output
    assert "ROSTER_COVERAGE UNVERIFIED" in output
    assert "HUMAN_ROSTER_COMPLETE PASS" in output
    assert output[-3:] == [
        "STOP_CHECK SESSION",
        "STOP_REASON VALIDATION_INCOMPLETE",
        "DOWNSTREAM_CHECKS_SKIPPED NO",
    ]


def test_first_reason_survives_later_cleanup_error() -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import StopReason

    report = Report()
    report.stop(Check.SCORING_STRUCTURE, StopReason.UNSUPPORTED_STAT_STRUCTURE)
    report.stop(Check.SESSION, StopReason.SESSION_ERROR, skipped=False)
    assert report.diagnostics() == (
        "STOP_CHECK SCORING_STRUCTURE",
        "STOP_REASON UNSUPPORTED_STAT_STRUCTURE",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
        "LAST_STOP_CHECK SESSION",
        "LAST_STOP_REASON SESSION_ERROR",
        "LAST_DOWNSTREAM_CHECKS_SKIPPED NO",
    )


@pytest.mark.parametrize("field", ["check", "reason", "skipped"])
def test_diagnostic_boundary_rejects_non_allowlisted_values(field: str) -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import StopReason

    report = Report()
    with pytest.raises(ValueError):
        if field == "check":
            report.stop("fake-private-input", StopReason.SESSION_ERROR)  # type: ignore[arg-type]
        elif field == "reason":
            report.stop(Check.SESSION, "fake-private-input")  # type: ignore[arg-type]
        else:
            report.stop(
                Check.SESSION,
                StopReason.SESSION_ERROR,
                skipped="fake-private-input",  # type: ignore[arg-type]
            )
    assert report.diagnostics() == ()


def test_unexpected_exception_never_escapes_into_diagnostics(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging

    code, _, _ = run_cli(monkeypatch, PAYLOADS)
    assert code == 0
    capsys.readouterr()

    def fail(report: Report) -> None:
        report.enter(Check.SCORING_STRUCTURE)
        logging.getLogger("fake-verifier").critical("private-exception-sentinel")
        raise RuntimeError("private-exception-sentinel <fake_xml>999.l.1001</fake_xml>")

    monkeypatch.setattr(cli, "_run_private", fail)
    assert cli.main() == 1
    captured = capsys.readouterr()
    assert "private-exception-sentinel" not in captured.out + captured.err
    assert "999.l." not in captured.out and not caplog.records
    assert captured.out.splitlines()[-3:] == [
        "STOP_CHECK SCORING_STRUCTURE",
        "STOP_REASON SESSION_ERROR",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]


def test_http_cleanup_error_is_attributed_to_session(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    @contextmanager
    def private_terminal() -> Iterator[None]:
        yield

    original_client = httpx.Client

    @contextmanager
    def cleanup_failure(
        *, transport: httpx.BaseTransport, trust_env: bool
    ) -> Iterator[httpx.Client]:
        transport.close()
        with original_client(
            transport=httpx.MockTransport(
                lambda request: pytest.fail("No HTTP expected")
            ),
            trust_env=False,
        ) as client:
            yield client
        raise RuntimeError("fake-private-cleanup-sentinel")

    def completed(
        token: SecretStr,
        *,
        http_client: httpx.Client,
        report: Report,
        choose: object,
        confirm: object,
        inspect_unsupported: object,
    ) -> None:
        for check in Check:
            if check is not Check.SESSION:
                report.mark(check, Status.PASS)
        report.enter(Check.HUMAN_ROSTER_COMPLETE)

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    monkeypatch.setattr(cli, "_private_terminal", private_terminal)
    monkeypatch.setattr(
        cli, "_read_hidden_input", lambda prompt: "APPROVE PRIVATE READ-ONLY"
    )
    monkeypatch.setattr(cli, "_authorize", lambda client: SecretStr("fake-token"))
    monkeypatch.setattr(cli, "verify_contracts", completed)
    monkeypatch.setattr(httpx, "Client", cleanup_failure)
    assert cli.main() == 1
    captured = capsys.readouterr()
    assert "SESSION FAIL" in captured.out
    assert "HUMAN_ROSTER_COMPLETE PASS" in captured.out
    assert "fake-private-cleanup-sentinel" not in captured.out + captured.err
    assert captured.out.splitlines()[-3:] == [
        "STOP_CHECK SESSION",
        "STOP_REASON SESSION_ERROR",
        "DOWNSTREAM_CHECKS_SKIPPED NO",
    ]
