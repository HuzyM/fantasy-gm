"""A known provider state can coexist with reported facts, never verified meaning."""

import pytest

from fantasy_gm.domain.roster import Roster
from tests.test_verifier_reporting import run_cli
from tests.test_yahoo_contract_verifier import PAYLOADS, ROSTER
from tests.test_yahoo_roster import parse


@pytest.mark.parametrize("value", ["0", "1"])
def test_prescoring_state_allows_only_reported_roster_facts(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    value: str,
) -> None:
    body = ROSTER.replace(
        b"</roster>", f"<is_prescoring>{value}</is_prescoring></roster>".encode()
    )
    roster = parse(body)
    assert isinstance(roster, Roster) and roster.context_unverified is True
    original = parse(ROSTER)
    assert isinstance(original, Roster)
    assert roster.entries == original.entries and roster.coverage == original.coverage
    payloads = PAYLOADS.copy()
    payloads[4] = body
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == 5
    assert "ROSTER_NORMALIZATION PASS" in output
    assert "ROSTER_COVERAGE UNVERIFIED" in output
    assert (
        "HUMAN_ROSTER_COMPLETE UNVERIFIED" in output and "SESSION UNVERIFIED" in output
    )


@pytest.mark.parametrize(
    "flag",
    [
        b"<is_prescoring/>",
        b"<is_prescoring>2</is_prescoring>",
        b"<is_prescoring><synthetic/></is_prescoring>",
        b"<is_editable>bad</is_editable>",
    ],
)
def test_invalid_optional_state_stays_unverified_without_erasing_players(
    flag: bytes,
) -> None:
    body = ROSTER.replace(b"<is_editable>1</is_editable>", flag)
    result = parse(body)
    assert isinstance(result, Roster) and result.context_unverified
    assert len(result.entries) == 2
    assert result.entries[0].selected_position == "C"
