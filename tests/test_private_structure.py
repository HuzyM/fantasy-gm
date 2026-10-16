"""Private structure only: invented XML, mocked HTTP and no authentication."""

import builtins
import io
import sys
from collections.abc import Iterator
from contextlib import contextmanager
from xml.etree import ElementTree as ET

import httpx
import pytest
from pydantic import SecretStr

from fantasy_gm import verify_nhl as cli
from fantasy_gm.providers.yahoo import contract_verifier as verifier
from tests.test_yahoo_contract_verifier import PAYLOADS, ROSTER, SETTINGS, run_fake


@pytest.mark.parametrize(
    "resource,old,new,needle,mismatch",
    [
        (
            1,
            b"</settings>",
            b"<synthetic_rule>private-value</synthetic_rule></settings>",
            "synthetic_rule",
            "Unrecognized direct field",
        ),
        (
            1,
            b"</settings>",
            b"<synthetic_0/><synthetic_1/><synthetic_2/><synthetic_3/>"
            b"<synthetic_4/><synthetic_5/></settings>",
            "synthetic_0",
            "Unrecognized direct field",
        ),
        (
            1,
            b"<settings>",
            b'<settings synthetic="private-value">',
            "synthetic",
            "Attributes are not supported",
        ),
        (
            1,
            b"</settings>",
            b'<draft_type synthetic="private-value"/></settings>',
            "draft_type",
            "Attributes are not supported",
        ),
        (
            1,
            b"</settings>",
            b"<draft_type><synthetic_child/></draft_type></settings>",
            "synthetic_child",
            "Administrative field must be scalar",
        ),
        (
            1,
            b"</settings>",
            b'<draft_type xmlns="https://private.invalid/ns"/></settings>',
            "draft_type",
            "Unexpected namespace",
        ),
        (
            4,
            b"</roster>",
            b"<synthetic_state>private-value</synthetic_state></roster>",
            "synthetic_state",
            "Unrecognized direct field",
        ),
        (
            4,
            b"<roster>",
            b'<roster synthetic="private-value">',
            "synthetic",
            "Attributes are not supported",
        ),
        (
            4,
            b"</roster>",
            b"<synthetic_wrapper><synthetic_child/></synthetic_wrapper></roster>",
            "synthetic_child",
            "Unrecognized direct field",
        ),
        (
            4,
            b"<is_editable>",
            b'<is_editable xmlns="https://private.invalid/ns">',
            "is_editable",
            "Unexpected namespace",
        ),
        (
            4,
            b'<players count="2">',
            b'<players count="2" synthetic="private-value">',
            "synthetic",
            "Attributes are not supported",
        ),
    ],
)
def test_only_rejected_structure_reaches_private_callback_without_changing_results(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
    resource: int,
    old: bytes,
    new: bytes,
    needle: str,
    mismatch: str,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[resource] = (SETTINGS if resource == 1 else ROSTER).replace(old, new)
    baseline, baseline_calls, _ = run_fake(payloads)
    assert isinstance(baseline, verifier.Report)
    report = verifier.Report()
    calls: list[httpx.Request] = []
    private: list[tuple[str, ...]] = []

    def handle(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        return httpx.Response(200, stream=httpx.ByteStream(payloads[len(calls) - 1]))

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected file access")

    with httpx.Client(transport=httpx.MockTransport(handle), trust_env=False) as client:
        with monkeypatch.context() as patch:
            patch.setattr(builtins, "open", deny)
            patch.setattr(io, "open", deny)
            verifier.verify_contracts(
                SecretStr("fake-token"),
                http_client=client,
                report=report,
                choose=lambda title, options: 0,
                confirm=lambda check, details: verifier.Status.PASS,
                inspect_unsupported=private.append,
            )
    assert report.lines() == baseline.lines()
    assert report.diagnostics() == baseline.diagnostics()
    assert len(calls) == len(baseline_calls) == 5
    assert len(private) == 1
    view = "\n".join(private[0])
    check = "SCORING_STRUCTURE" if resource == 1 else "ROSTER_STRUCTURE"
    assert check in view and needle in view and mismatch in view
    parent = "league/settings" if resource == 1 else "team/roster"
    if old in {b"<settings>", b"<roster>"}:
        parent = "league" if resource == 1 else "team"
        assert "stat_categories" not in view and "coverage_type" not in view
    assert f"Parent path: {parent}" in view
    assert "UNVERIFIED" in view and "namespace:" in view
    if needle == "synthetic_0":
        assert view.count("Check:") == 4 and "synthetic_4" not in view
    assert not caplog.records
    for secret in (
        "private-value",
        "private.invalid",
        "999.l.",
        "999.p.",
        "Invented",
        "2099-10-15",
        "0.123456789",
        "fake-token",
    ):
        assert secret not in view
        assert secret not in repr(vars(report))


def test_structure_names_are_escaped_bounded_and_do_not_reveal_namespace_urls() -> None:
    node = ET.Element("{https://private.invalid/ns}" + "é\x1b\n\u202e" * 300)
    node.set("{https://private.invalid/attr}evil\x1b\n", "private-value")
    node.text = "private-value"
    child = ET.SubElement(node, "child\x1b")
    child.tail = "private-value"
    for index in range(6):
        node.set(f"attribute_{index}", "private-value")
        ET.SubElement(node, f"child_{index}").text = "private-value"
    details = verifier._structure(
        node,
        parent="team/roster",
        ns="urn:expected",
        check=verifier.Check.ROSTER_STRUCTURE,
        mismatch="Unrecognized direct field",
        known=False,
    )
    view = "\n".join(details)
    assert "MIXED" in view and "truncated" in view
    assert "\\x1b" in view and "\\n" in view and "\\u202e" in view
    assert "\x1b" not in view and "\u202e" not in view
    assert all(ord(c) < 128 for c in view)
    assert len(view) < 1800
    assert "private-value" not in view and "https://" not in view
    assert "attribute_5" not in view and "child_5" not in view


@pytest.mark.parametrize("answer", ["NEXT", "UNKNOWN"])
def test_inspection_acknowledgement_never_confirms_semantics(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], answer: str
) -> None:
    monkeypatch.setattr(cli, "_read_hidden_input", lambda prompt: answer)
    cli._inspect_unsupported(("SCORING_STRUCTURE UNVERIFIED",))
    view = capsys.readouterr().out
    assert "does not mean Yahoo data is invalid" in view
    assert "NEXT" in view and "UNKNOWN" in view and "does not approve" in view


@pytest.mark.parametrize("answer", ["CANCEL", "CONFIRM", "", "CONTINUE"])
def test_other_inspection_answers_interrupt(
    monkeypatch: pytest.MonkeyPatch, answer: str
) -> None:
    monkeypatch.setattr(cli, "_show", lambda details: None)
    monkeypatch.setattr(cli, "_read_hidden_input", lambda prompt: answer)
    with pytest.raises(KeyboardInterrupt):
        cli._inspect_unsupported(())


@pytest.mark.parametrize(
    "outcome", ["NEXT", "UNKNOWN", "CANCEL", "error", "display_error"]
)
def test_private_structure_clears_before_fixed_summary_even_on_interruption(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    outcome: str,
) -> None:
    # Exercise the real terminal context and cleanup, without OAuth/configuration.
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", b"<synthetic_rule>private-value</synthetic_rule></settings>"
    )
    payloads[4] = ROSTER.replace(b"<roster>", b'<roster synthetic="private-value">')
    calls: list[httpx.Request] = []

    @contextmanager
    def modes() -> Iterator[None]:
        yield

    def run(report: verifier.Report) -> None:
        def handle(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            return httpx.Response(
                200, stream=httpx.ByteStream(payloads[len(calls) - 1])
            )

        report.mark(verifier.Check.LIVE_APPROVAL, verifier.Status.PASS)
        report.mark(verifier.Check.AUTHORIZATION, verifier.Status.PASS)
        with httpx.Client(
            transport=httpx.MockTransport(handle), trust_env=False
        ) as client:
            verifier.verify_contracts(
                SecretStr("fake-token"),
                http_client=client,
                report=report,
                choose=lambda title, options: 0,
                confirm=lambda check, details: verifier.Status.PASS,
                inspect_unsupported=cli._inspect_unsupported,
            )

    def answer(prompt: str) -> str:
        if "NEXT or UNKNOWN" not in prompt:
            return "NEXT"  # Pagination only acknowledges another private page.
        if outcome == "error":
            raise ValueError("private-exception")
        return outcome

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(cli, "_terminal_modes", modes)
    monkeypatch.setattr(cli, "_run_private", run)
    monkeypatch.setattr(cli, "_read_hidden_input", answer)
    if outcome == "display_error":

        def display_failure(details: tuple[str, ...]) -> None:
            raise ValueError("private-display-error")

        monkeypatch.setattr(cli, "_show", display_failure)
    assert cli.main() == 1
    captured = capsys.readouterr()
    private, summary = captured.out.split(cli._LEAVE_PRIVATE)
    assert ("synthetic_rule" in private) is (outcome != "display_error")
    assert len(calls) == (5 if outcome in {"NEXT", "UNKNOWN"} else 2)
    if outcome in {"NEXT", "UNKNOWN"}:
        assert "ROSTER_STRUCTURE UNVERIFIED" in private
        assert "LAST_STOP_CHECK ROSTER_STRUCTURE" in summary
    assert "private-" not in captured.out and not captured.err
    assert "synthetic" not in summary and "999." not in summary
    assert (
        "SESSION " + ("UNVERIFIED" if outcome in {"NEXT", "UNKNOWN"} else "FAIL")
        in summary
    )
    for line in summary.splitlines():
        field, value = line.split()
        assert field in {c.value for c in verifier.Check} | {
            "STOP_CHECK",
            "STOP_REASON",
            "DOWNSTREAM_CHECKS_SKIPPED",
            "LAST_STOP_CHECK",
            "LAST_STOP_REASON",
            "LAST_DOWNSTREAM_CHECKS_SKIPPED",
        }
        assert value in {c.value for c in verifier.Check} | {
            s.value for s in verifier.Status
        } | {r.value for r in verifier.StopReason} | {"YES", "NO"}


def test_terminal_setup_failure_prevents_inspection(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    @contextmanager
    def modes() -> Iterator[None]:
        raise ValueError("private-terminal-error")
        yield

    def forbidden(report: verifier.Report) -> None:
        raise AssertionError("Private work must not start")

    monkeypatch.setattr(sys, "argv", ["verifier", "--interactive"])
    for stream in (sys.stdin, sys.stdout, sys.stderr):
        monkeypatch.setattr(stream, "isatty", lambda: True)
    monkeypatch.setattr(cli, "_terminal_modes", modes)
    monkeypatch.setattr(cli, "_run_private", forbidden)
    assert cli.main() == 1
    captured = capsys.readouterr()
    assert "PRIVATE_TERMINAL FAIL" in captured.out
    assert "private-" not in captured.out and cli._ENTER_PRIVATE not in captured.out
    assert not captured.err
