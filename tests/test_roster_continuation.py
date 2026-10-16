"""Reproduce masked independent stops with invented XML and mocked HTTP only."""

from collections.abc import Callable

import pytest

from fantasy_gm.providers.yahoo.contract_verifier import Check, SelectionCancelled
from tests.test_verifier_reporting import ORIGINAL_STATUSES, run_cli
from tests.test_yahoo_contract_verifier import PAYLOADS, ROSTER, SETTINGS


def payloads_with_unverified_scoring() -> list[bytes]:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(b"</settings>", b"<synthetic_rule/></settings>")
    return payloads


def choose_for(scenario: str) -> Callable[[str, tuple[str, ...]], int | None]:
    def choose(title: str, options: tuple[str, ...]) -> int | None:
        if title != "Select your owned team":
            return 0
        if scenario == "missing":
            return None
        if scenario == "cancelled":
            raise SelectionCancelled()
        return 0

    return choose


@pytest.mark.parametrize("scenario", ["missing", "cancelled", "unsupported_envelope"])
def test_identical_reported_status_pattern_can_hide_distinct_execution_paths(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scenario: str,
) -> None:
    payloads = payloads_with_unverified_scoring()
    if scenario == "unsupported_envelope":
        payloads[4] = ROSTER.replace(
            b"<roster>", b'<roster synthetic="private-sentinel">'
        )
    code, calls, _ = run_cli(monkeypatch, payloads, choose=choose_for(scenario))
    output = capsys.readouterr().out.splitlines()
    team_checks = {
        "OWNED_TEAM_MEMBERSHIP",
        "LEAGUE_TEAMS_STRUCTURE",
        "LEAGUE_TEAMS_COMPLETENESS",
        "HUMAN_LEAGUE_TEAMS_COMPLETE",
    }
    expected = [
        line.replace(" UNVERIFIED", " PASS") if line.split()[0] in team_checks else line
        for line in ORIGINAL_STATUSES
    ]
    assert code == 1 and output[: len(Check)] == expected
    assert output[len(Check) : len(Check) + 3] == [
        "STOP_CHECK SCORING_STRUCTURE",
        "STOP_REASON UNSUPPORTED_SCORING_SETTING",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
    ]
    assert len(calls) == (5 if scenario == "unsupported_envelope" else 4)
    assert sum(request.url.path.endswith("/roster") for request in calls) == (
        1 if scenario == "unsupported_envelope" else 0
    )
    assert not any(
        value in "\n".join(output)
        for value in ("private-sentinel", "Invented", "999.l.", "synthetic_rule")
    )


@pytest.mark.parametrize(
    "scenario,check,reason",
    [
        ("missing", "OWNED_TEAM_MEMBERSHIP", "SELECTION_NOT_COMPLETED"),
        ("cancelled", "OWNED_TEAM_MEMBERSHIP", "USER_CANCELLED"),
        ("unsupported_envelope", "ROSTER_STRUCTURE", "UNSUPPORTED_STRUCTURE"),
    ],
)
def test_later_actual_stop_is_not_hidden_by_scoring_reason(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    scenario: str,
    check: str,
    reason: str,
) -> None:
    payloads = payloads_with_unverified_scoring()
    if scenario == "unsupported_envelope":
        payloads[4] = ROSTER.replace(
            b"<roster>", b'<roster synthetic="private-sentinel">'
        )
    code, _, _ = run_cli(monkeypatch, payloads, choose=choose_for(scenario))
    assert code == 1
    assert capsys.readouterr().out.splitlines()[-3:] == [
        f"LAST_STOP_CHECK {check}",
        f"LAST_STOP_REASON {reason}",
        "LAST_DOWNSTREAM_CHECKS_SKIPPED YES",
    ]


def test_explicit_owned_selection_reaches_normalization_without_scoring_or_slots(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    payloads = payloads_with_unverified_scoring()
    payloads[1] = payloads[1].replace(
        b"<count>2</count>", b"<count>2</count><synthetic_slot_rule/>"
    )
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == 5
    assert "ROSTER_STRUCTURE PASS" in output and "ROSTER_NORMALIZATION PASS" in output
    assert (
        "ROSTER_SLOTS UNVERIFIED" in output
        and "ROSTER_SLOT_CAPACITY UNVERIFIED" in output
    )
    assert "SESSION UNVERIFIED" in output


@pytest.mark.parametrize("answer", ["", "not-a-number", "2"])
def test_invalid_private_team_choice_never_requests_a_roster(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], answer: str
) -> None:
    from fantasy_gm import verify_nhl as cli

    monkeypatch.setattr(cli, "_show", lambda details: None)
    monkeypatch.setattr(cli, "_read_hidden_input", lambda prompt: answer)

    def choose(title: str, options: tuple[str, ...]) -> int | None:
        return cli._choose(title, options) if title == "Select your owned team" else 0

    code, calls, _ = run_cli(
        monkeypatch, payloads_with_unverified_scoring(), choose=choose
    )
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == 4
    assert not any(request.url.path.endswith("/roster") for request in calls)
    assert "LAST_STOP_REASON SELECTION_NOT_COMPLETED" in output
    assert "ROSTER_NORMALIZATION UNVERIFIED" in output


@pytest.mark.parametrize("kind", ["unowned", "wrong_team", "missing_player_id"])
def test_real_identity_prerequisites_remain_failures_after_scoring_stop(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], kind: str
) -> None:
    payloads = payloads_with_unverified_scoring()
    if kind == "unowned":
        payloads[2] = payloads[2].replace(b"999.l.1001.t.1", b"999.l.1002.t.1")
        check, expected_calls = "OWNED_TEAM_MEMBERSHIP", 3
    elif kind == "wrong_team":
        payloads[4] = ROSTER.replace(b"999.l.1001.t.1", b"999.l.1001.t.2")
        check, expected_calls = "ROSTER_STRUCTURE", 5
    else:
        payloads[4] = ROSTER.replace(b"<player_id>802</player_id>", b"")
        check, expected_calls = "ROSTER_NORMALIZATION", 5
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == expected_calls
    assert f"{check} FAIL" in output and "SESSION FAIL" in output
    assert f"LAST_STOP_CHECK {check}" in output
    assert "LAST_STOP_REASON VALIDATION_FAILED" in output
    assert "HUMAN_ROSTER_COMPLETE UNVERIFIED" in output


def test_later_stop_reporting_has_no_private_io_or_dynamic_fields(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
) -> None:
    import builtins
    import io

    from fantasy_gm.providers.yahoo.contract_verifier import Status, StopReason

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected filesystem access")

    payloads = payloads_with_unverified_scoring()
    payloads[4] = ROSTER.replace(b"<roster>", b'<roster synthetic="private-sentinel">')
    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        code, _, _ = run_cli(patch, payloads)
    assert code == 1 and not caplog.records
    output = capsys.readouterr()
    allowed = {check.value: {status.value for status in Status} for check in Check}
    allowed.update(
        {
            "STOP_CHECK": {check.value for check in Check},
            "LAST_STOP_CHECK": {check.value for check in Check},
            "STOP_REASON": {reason.value for reason in StopReason},
            "LAST_STOP_REASON": {reason.value for reason in StopReason},
            "DOWNSTREAM_CHECKS_SKIPPED": {"YES", "NO"},
            "LAST_DOWNSTREAM_CHECKS_SKIPPED": {"YES", "NO"},
        }
    )
    for line in output.out.splitlines():
        field, value = line.split()
        assert field in allowed and value in allowed[field]
    assert not output.err


def test_stop_tracking_is_bounded_and_rejects_private_input_before_mutation() -> None:
    from fantasy_gm.providers.yahoo.contract_verifier import Report, StopReason

    report = Report()
    report.stop(Check.SCORING_STRUCTURE, StopReason.UNSUPPORTED_SCORING_SETTING)
    report.stop(Check.ROSTER_STRUCTURE, StopReason.UNSUPPORTED_STRUCTURE)
    report.stop(Check.SESSION, StopReason.SESSION_ERROR, skipped=False)
    before = report.diagnostics()
    with pytest.raises(ValueError):
        report.stop(Check.SESSION, "private-sentinel")  # type: ignore[arg-type]
    assert report.diagnostics() == before and len(before) == 6
    assert before[-3:] == (
        "LAST_STOP_CHECK SESSION",
        "LAST_STOP_REASON SESSION_ERROR",
        "LAST_DOWNSTREAM_CHECKS_SKIPPED NO",
    )
