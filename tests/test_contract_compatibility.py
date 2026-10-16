"""Compatibility audit regressions; every XML value is wholly invented."""

import builtins
import io
import re

import pytest

from fantasy_gm.domain.roster import Roster
from fantasy_gm.providers.yahoo.contract_verifier import Check
from tests.test_verifier_reporting import ORIGINAL_STATUSES, run_cli
from tests.test_yahoo_contract_verifier import NS, PAYLOADS, ROSTER, SETTINGS
from tests.test_yahoo_roster import parse


@pytest.mark.parametrize(
    "roster",
    [
        ROSTER.replace(b"<roster>", b'<roster synthetic="invented-private">'),
        ROSTER.replace(b"</roster>", b"<synthetic_state/></roster>"),
        ROSTER.replace(b"<is_editable>", b'<is_editable xmlns="urn:invented">'),
        ROSTER.replace(b"<date>", b'<date synthetic="invented-private">', 1),
        ROSTER.replace(b'<players count="2">', b'<players count="2" start="0">'),
    ],
    ids=[
        "wrapper_attribute",
        "unknown_wrapper_child",
        "child_namespace",
        "scalar_attribute",
        "collection_extra_attribute",
    ],
)
def test_distinct_envelope_shapes_reproduce_latest_two_stop_status_pattern(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    caplog: pytest.LogCaptureFixture,
    roster: bytes,
) -> None:
    payloads = PAYLOADS.copy()
    payloads[1] = SETTINGS.replace(b"</settings>", b"<synthetic_rule/></settings>")
    payloads[4] = roster

    def deny(*args: object, **kwargs: object) -> None:
        raise AssertionError("Unexpected filesystem access")

    with monkeypatch.context() as patch:
        patch.setattr(builtins, "open", deny)
        patch.setattr(io, "open", deny)
        code, calls, prompts = run_cli(patch, payloads)
    captured = capsys.readouterr()
    output = captured.out.splitlines()
    passed = {
        "OWNED_TEAM_MEMBERSHIP",
        "LEAGUE_TEAMS_STRUCTURE",
        "LEAGUE_TEAMS_COMPLETENESS",
        "HUMAN_LEAGUE_TEAMS_COMPLETE",
    }
    assert output[: len(Check)] == [
        line.replace(" UNVERIFIED", " PASS") if line.split()[0] in passed else line
        for line in ORIGINAL_STATUSES
    ]
    assert output[len(Check) :] == [
        "STOP_CHECK SCORING_STRUCTURE",
        "STOP_REASON UNSUPPORTED_SCORING_SETTING",
        "DOWNSTREAM_CHECKS_SKIPPED YES",
        "LAST_STOP_CHECK ROSTER_STRUCTURE",
        "LAST_STOP_REASON UNSUPPORTED_STRUCTURE",
        "LAST_DOWNSTREAM_CHECKS_SKIPPED YES",
    ]
    assert code == 1 and len(calls) == 5
    assert sum(request.url.path.endswith("/roster") for request in calls) == 1
    assert prompts == [Check.HUMAN_LEAGUE_TEAMS_COMPLETE]
    assert not captured.err and not caplog.records


@pytest.mark.parametrize(
    "setting",
    [
        b'<draft_type synthetic="invented-private">offline</draft_type>',
        b"<draft_type><synthetic_child/></draft_type>",
        b'<draft_type xmlns="urn:invented">offline</draft_type>',
        b'<uses_negative_points synthetic="invented-private">1</uses_negative_points>',
    ],
    ids=[
        "metadata_attribute",
        "metadata_container",
        "metadata_namespace",
        "flag_attribute",
    ],
)
def test_familiar_setting_name_does_not_establish_an_unfamiliar_shape(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    setting: bytes,
) -> None:
    payloads = PAYLOADS.copy()
    if b"uses_negative_points" in setting:
        payloads[1] = SETTINGS.replace(
            b"<uses_negative_points>1</uses_negative_points>", setting
        )
    else:
        payloads[1] = SETTINGS.replace(b"</settings>", setting + b"</settings>")
    code, calls, _ = run_cli(monkeypatch, payloads)
    output = capsys.readouterr().out
    assert code == 1 and len(calls) == 5
    assert "STOP_REASON UNSUPPORTED_SCORING_SETTING" in output
    assert "SCORING_STRUCTURE UNVERIFIED" in output
    assert "MODIFIER_VALUES UNVERIFIED" in output
    assert "ROSTER_NORMALIZATION PASS" in output
    assert "SESSION UNVERIFIED" in output
    assert "invented-private" not in output and "draft_type" not in output


def test_ordinary_team_and_player_metadata_preserve_normalized_roster() -> None:
    body = ROSTER.replace(
        b"<roster>",
        b"<team_logos><team_logo><size>large</size><url>invented-private</url>"
        b"</team_logo></team_logos><managers><manager><nickname>invented-private"
        b"</nickname></manager></managers><roster>",
    ).replace(
        b"</player>",
        b"<status>invented-private</status><editorial_team_abbr>ZZZ</editorial_team_abbr>"
        b"<headshot><url>invented-private</url></headshot></player>",
    )
    result = parse(body)
    baseline = parse(ROSTER)
    assert isinstance(result, Roster) and isinstance(baseline, Roster)
    # FGM-007 retains this optional code; all earlier roster facts stay identical.
    expected = baseline.model_copy(
        update={
            "entries": tuple(
                entry.model_copy(update={"professional_team_code": "ZZZ"})
                for entry in baseline.entries
            )
        }
    )
    assert result == expected
    assert "invented-private" not in repr(result)


@pytest.mark.parametrize("namespace", [NS, NS.replace("http:", "https:")])
def test_explicit_namespace_prefix_is_already_supported(namespace: str) -> None:
    # XML namespace declarations are bindings, not ElementTree attributes.
    body = ROSTER.replace(f'xmlns="{NS}"'.encode(), f'xmlns:y="{namespace}"'.encode())
    body = re.sub(rb"<(/?)([a-z_]+)", rb"<\1y:\2", body)
    result = parse(body)
    assert isinstance(result, Roster) and result == parse(ROSTER)
