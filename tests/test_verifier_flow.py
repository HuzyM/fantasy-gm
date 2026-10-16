"""Synthetic scoring isolation and private setting-name inspection regressions."""

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm.providers.yahoo.contract_verifier import (
    Check,
    Report,
    Status,
    verify_contracts,
)
from tests.test_verifier_reporting import run_cli
from tests.test_yahoo_contract_verifier import PAYLOADS, SETTINGS, lines, run_fake


@pytest.mark.parametrize(
    "name", ["draft_type", "max_teams", "waiver_type", "trade_end_date"]
)
def test_public_administrative_scalar_settings_are_not_scoring(name: str) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", f"<{name}>invented</{name}></settings>".encode()
    )
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE PASS" in lines(report)


@pytest.mark.parametrize(
    "name",
    [
        "scoring_bonus",
        "synthetic_trade_status",
        "synthetic_extension",
    ],
)
def test_unknown_settings_do_not_certify_scoring_but_allow_roster(name: str) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", f"<{name}>fake-private-value</{name}></settings>".encode()
    )
    report, calls, _ = run_fake(payloads)
    assert isinstance(report, Report)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE UNVERIFIED" in lines(report)
    assert "MODIFIER_VALUES UNVERIFIED" in lines(report)
    assert "HUMAN_SCORING_COMPLETE UNVERIFIED" in lines(report)
    assert "ROSTER_SLOTS PASS" in lines(report)
    assert "OWNED_TEAM_MEMBERSHIP PASS" in lines(report)
    assert "HUMAN_ROSTER_COMPLETE PASS" in lines(report)
    assert report.diagnostics() == (
        "STOP_CHECK SCORING_STRUCTURE",
        "STOP_REASON UNSUPPORTED_SCORING_SETTING",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    )
    assert name not in repr(vars(report)) and "fake-private-value" not in repr(
        vars(report)
    )


@pytest.mark.parametrize("human", [Status.UNVERIFIED, Status.FAIL])
def test_scoring_human_unknown_can_continue_but_rejection_stops(human: Status) -> None:
    # Only the scoring-format prompt is uncertain/rejected; other comparisons pass.
    prompts: list[Check] = []
    calls: list[httpx.Request] = []
    report = Report()

    def confirm(check: Check, details: tuple[str, ...]) -> Status:
        prompts.append(check)
        return human if check is Check.HUMAN_POINTS_FORMAT else Status.PASS

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(PAYLOADS[len(calls) - 1]))

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        verify_contracts(
            SecretStr("fake-token"),
            http_client=client,
            report=report,
            choose=lambda title, options: 0,
            confirm=confirm,
        )
    assert len(calls) == (5 if human is Status.UNVERIFIED else 2)
    assert f"HUMAN_POINTS_FORMAT {human.value}" in report.lines()
    assert report.passed(Check.HUMAN_ROSTER_COMPLETE) is (human is Status.UNVERIFIED)
    assert Check.HUMAN_SCORING_COMPLETE not in prompts


def test_original_setting_stop_now_finishes_independent_checks_without_session_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", b"<synthetic_trade_status/></settings>"
    )
    code, calls, prompts = run_cli(monkeypatch, payloads)
    output = capsys.readouterr()
    assert code == 1 and len(calls) == 5
    assert Check.HUMAN_SCORING_COMPLETE not in prompts
    assert "SESSION UNVERIFIED" in output.out
    assert "HUMAN_ROSTER_COMPLETE PASS" in output.out
    assert "synthetic_trade_status" not in output.out + output.err


@pytest.mark.parametrize("kind", ["identity", "authorization", "xml", "ownership"])
def test_real_prerequisite_failure_still_stops_requests(kind: str) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", b"<synthetic_trade_status/></settings>"
    )
    calls: list[httpx.Request] = []
    if kind == "identity":
        payloads[1] = payloads[1].replace(b"999.l.1001", b"999.l.1002")
    elif kind == "xml":
        payloads[1] = b"<!DOCTYPE fantasy_content>" + payloads[1]
    elif kind == "ownership":
        payloads[2] = payloads[2].replace(b"999.l.1001.t.1", b"999.l.1002.t.1")

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(
            401 if kind == "authorization" and len(calls) == 2 else 200,
            stream=httpx.ByteStream(payloads[len(calls) - 1]),
        )

    report = Report()
    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        verify_contracts(
            SecretStr("fake-token"),
            http_client=client,
            report=report,
            choose=lambda title, options: 0,
            confirm=lambda check, details: Status.PASS,
        )
    assert len(calls) == (3 if kind == "ownership" else 2)
    assert report.failed() and not report.passed(Check.ROSTER_STRUCTURE)


def test_unsupported_setting_names_only_reach_private_callback() -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>",
        b"<synthetic_trade_status>fake-private-value</synthetic_trade_status></settings>",
    )
    private: list[str] = []
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    report = Report()
    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        verify_contracts(
            SecretStr("fake-token"),
            http_client=client,
            report=report,
            choose=lambda title, options: 0,
            confirm=lambda check, details: Status.PASS,
            inspect_unsupported=private.extend,
        )
    assert any("synthetic_trade_status" in value for value in private)
    assert not any("fake-private-value" in value for value in private)
    assert "synthetic_trade_status" not in repr(vars(report)) + "\n".join(
        report.diagnostics()
    )


def test_known_metadata_cannot_hide_scoring_children() -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>",
        b"<draft_type><scoring_bonus>fake</scoring_bonus></draft_type></settings>",
    )
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert isinstance(report, Report)
    assert not report.passed(Check.SCORING_STRUCTURE)


@pytest.mark.parametrize(
    "field",
    ["settings", "scoring_type", "uses_fractional_points", "uses_negative_points"],
)
def test_unknown_attributes_never_certify_scoring(field: str) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        f"<{field}>".encode(), f'<{field} bonus="fake-private">'.encode()
    )
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE UNVERIFIED" in lines(report)
    assert "HUMAN_SCORING_COMPLETE UNVERIFIED" in lines(report)
    assert "HUMAN_ROSTER_COMPLETE PASS" in lines(report)


def test_slot_failure_preserves_independent_roster_but_not_capacity() -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(b"<count>2</count>", b"<count>-1</count>")
    report, calls, _ = run_fake(payloads)
    assert isinstance(report, Report)
    assert len(calls) == 5
    assert report.passed(Check.OWNED_TEAM_MEMBERSHIP)
    assert report.passed(Check.HUMAN_LEAGUE_TEAMS_COMPLETE)
    assert "ROSTER_SLOTS FAIL" in report.lines()
    assert "ROSTER_STRUCTURE PASS" in report.lines()
    assert "ROSTER_NORMALIZATION PASS" in report.lines()
    assert "ROSTER_SLOT_CAPACITY UNVERIFIED" in report.lines()


@pytest.mark.parametrize("kind", ["namespace", "attribute", "duplicate"])
def test_metadata_exemption_is_exact_and_not_a_structure_bypass(kind: str) -> None:
    extension = {
        "namespace": b'<draft_type xmlns="urn:synthetic">fake</draft_type>',
        "attribute": b'<draft_type fake="private">fake</draft_type>',
        "duplicate": b"<draft_type>fake</draft_type><draft_type>fake</draft_type>",
    }[kind]
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(b"</settings>", extension + b"</settings>")
    report, _, _ = run_fake(payloads)
    assert isinstance(report, Report)
    assert not report.passed(Check.SCORING_STRUCTURE)


@pytest.mark.parametrize("failed_resource", [2, 4])
def test_later_failure_overrides_session_uncertainty(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    failed_resource: int,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", b"<synthetic_trade_status/></settings>"
    )
    if failed_resource == 2:
        payloads[2] = payloads[2].replace(b"999.l.1001.t.1", b"999.l.1002.t.1")
    else:
        payloads[4] = payloads[4].replace(b"<player_id>802</player_id>", b"")
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == failed_resource + 1
    assert "SCORING_STRUCTURE UNVERIFIED" in output
    assert "SESSION FAIL" in output


def test_private_inspection_is_cleared_before_allowlisted_summary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    import logging
    import sys
    from collections.abc import Iterator
    from contextlib import contextmanager

    from fantasy_gm import verify_nhl as cli

    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>",
        "<synthetic_é>fake-private-value</synthetic_é></settings>".encode(),
    )
    calls: list[httpx.Request] = []

    def handle(request: httpx.Request) -> httpx.Response:
        logging.critical("fake-private-log")
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    @contextmanager
    def terminal() -> Iterator[None]:
        print(cli._ENTER_PRIVATE, end="")
        try:
            yield
        finally:
            print(cli._LEAVE_PRIVATE, end="")

    def run(report: Report) -> None:
        report.mark(Check.LIVE_APPROVAL, Status.PASS)
        report.mark(Check.AUTHORIZATION, Status.PASS)
        with httpx.Client(
            transport=httpx.MockTransport(handle), trust_env=False
        ) as client:
            verify_contracts(
                SecretStr("fake-token"),
                http_client=client,
                report=report,
                choose=lambda title, options: 0,
                confirm=lambda check, details: Status.PASS,
                inspect_unsupported=cli._inspect_unsupported,
            )

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    monkeypatch.setattr(cli, "_private_terminal", terminal)
    monkeypatch.setattr(cli, "_run_private", run)
    monkeypatch.setattr(cli, "_read_hidden_input", lambda prompt: "NEXT")
    assert cli.main() == 1
    output = capsys.readouterr()
    private, summary = output.out.split(cli._LEAVE_PRIVATE)
    assert "synthetic_\\xe9" in private
    assert "fake-private-value" not in output.out + output.err
    assert "synthetic" not in summary and not caplog.records
    assert "HUMAN_ROSTER_COMPLETE PASS" in summary
    assert "SESSION UNVERIFIED" in summary


def test_last_scoring_confirmation_does_not_claim_skipped_independent_checks() -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import _human, _Stop

    report = Report()
    with pytest.raises(_Stop):
        _human(
            report,
            Check.HUMAN_POSITION_SCOPES,
            (),
            lambda check, details: Status.UNVERIFIED,
        )
    assert report.diagnostics()[-1] == "DOWNSTREAM_CHECKS_SKIPPED NO"
