"""Publicly described administrative settings, with invented values only."""

import pytest

from fantasy_gm.providers.yahoo.contract_verifier import Report
from tests.test_yahoo_contract_verifier import PAYLOADS, SETTINGS, lines, run_fake


@pytest.mark.parametrize(
    "name",
    [
        "can_trade_draft_picks",
        "has_playoff_consolation_games",
        "max_weekly_adds",
        "num_playoff_consolation_teams",
        "num_playoff_teams",
        "playoff_start_week",
        "roster_import_deadline",
        "uses_lock_eliminated_teams",
        "uses_playoff",
        "uses_playoff_reseeding",
        "uses_roster_import",
    ],
)
def test_documented_administrative_scalar_does_not_block_stat_weights(
    name: str,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(
        b"</settings>", f"<{name}>1</{name}></settings>".encode()
    )
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE PASS" in lines(report)


DIVISIONS = (
    b'<divisions count="1"><division><division_id>1</division_id>'
    b"<name>Invented Division</name></division></divisions>"
)


@pytest.mark.parametrize("divisions", [DIVISIONS, b"<divisions/>"])
def test_documented_division_identity_shape_is_non_scoring_metadata(
    divisions: bytes,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(b"</settings>", divisions + b"</settings>")
    report, calls, _ = run_fake(payloads)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE PASS" in lines(report)
    assert "Invented Division" not in "\n".join(lines(report))


@pytest.mark.parametrize(
    "metadata",
    [
        DIVISIONS.replace(b"</division>", b"<bonus>fake</bonus></division>"),
        DIVISIONS.replace(b"<division>", b'<division rule="fake">'),
        DIVISIONS.replace(b"<name>", b'<name xmlns="urn:synthetic">'),
        b"<synthetic_rule>fake</synthetic_rule>",
        b"<league_premium_features/>",
        b"<uses_playoff><bonus>fake</bonus></uses_playoff>",
    ],
)
def test_administrative_exclusions_never_admit_unknown_rules(metadata: bytes) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(b"</settings>", metadata + b"</settings>")
    report, calls, _ = run_fake(payloads)
    assert isinstance(report, Report)
    assert len(calls) == 5
    assert "SCORING_STRUCTURE UNVERIFIED" in lines(report)
    assert "HUMAN_SCORING_COMPLETE UNVERIFIED" in lines(report)
    assert "UNSUPPORTED_SCORING_SETTING" in report.diagnostics()[1]
