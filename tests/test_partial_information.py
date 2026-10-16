"""Actual failure modes reproduced with invented responses, never live data."""

from decimal import Decimal

import pytest

from fantasy_gm.domain.roster import Roster
from fantasy_gm.providers.yahoo.fantasy import YahooFantasyError
from fantasy_gm.providers.yahoo.settings import parse_league_settings
from tests.test_yahoo_contract_verifier import ROSTER, SETTINGS
from tests.test_yahoo_roster import parse


@pytest.mark.parametrize(
    "extra",
    [
        b"<synthetic_administration><label>private-value</label></synthetic_administration>",
        b"<synthetic_scoring_bonus><value>99</value></synthetic_scoring_bonus>",
    ],
)
def test_unknown_settings_do_not_erase_known_fields_or_certify_complete_rules(
    extra: bytes,
) -> None:
    result = parse_league_settings(
        SETTINGS.replace(b"</settings>", extra + b"</settings>"),
        league_key="999.l.1001",
    )
    assert result.scoring is not None and result.scoring.incomplete
    assert result.scoring.rules[0].modifier == Decimal(
        "0.12345678901234567890123456789"
    )
    assert result.scoring.rules[1].modifier == Decimal("-2.50")
    assert result.scoring.rules[2].modifier == Decimal("0")
    assert result.scoring.rules[3].modifier is None
    assert result.roster_slots is not None and not result.roster_slots_incomplete


def test_scoped_unknown_rule_keeps_known_modifier_without_certifying_its_meaning() -> (
    None
):
    body = SETTINGS.replace(
        b"<value>-2.50</value>", b"<value>-2.50</value><synthetic_bonus/>"
    )
    scoring = parse_league_settings(body, league_key="999.l.1001").scoring
    assert scoring is not None and scoring.incomplete
    assert scoring.rules[1].modifier == Decimal("-2.50")


def test_bad_optional_weight_and_scope_leave_other_known_information_available() -> (
    None
):
    body = SETTINGS.replace(b"<value>-2.50</value>", b"<value>bad</value>").replace(
        b"<position_type>G</position_type><is_only_display_stat>1",
        b"<position_type>G</position_type><is_only_display_stat>bad",
    )
    scoring = parse_league_settings(body, league_key="999.l.1001").scoring
    assert scoring is not None and scoring.incomplete
    assert scoring.rules[1].modifier is None
    assert scoring.rules[2].modifier == Decimal("0")
    assert (
        scoring.rules[0].scopes is None
        or scoring.rules[0].scopes[1].display_only is None
    )


@pytest.mark.parametrize(
    "body",
    [
        ROSTER.replace(b"<roster>", b'<roster synthetic="private-value">'),
        ROSTER.replace(
            b"</roster>",
            b"<synthetic_metadata><label>private-value</label></synthetic_metadata></roster>",
        ),
        ROSTER.replace(b"<date>2099-10-15</date>", b"<date><synthetic/></date>", 1),
    ],
)
def test_outer_metadata_or_unsupported_coverage_never_erases_valid_players(
    body: bytes,
) -> None:
    result = parse(body)
    assert isinstance(result, Roster) and result.context_unverified
    assert [player.provider_player_id for player in result.entries] == [
        "999.p.801",
        "999.p.802",
    ]
    assert result.entries[0].selected_position == "C"
    assert result.entries[0].eligible_positions == ("C", "LW")


def test_unsupported_positions_do_not_erase_identity_or_other_players() -> None:
    body = ROSTER.replace(
        b"<eligible_positions>", b'<eligible_positions synthetic="private-value">', 1
    )
    result = parse(body)
    assert isinstance(result, Roster) and result.context_unverified
    assert result.entries[0].eligible_positions is None
    assert result.entries[0].selected_position == "C"
    assert result.entries[1].eligible_positions == ("G",)


@pytest.mark.parametrize(
    "old,new",
    [
        (b"999.l.1001.t.1", b"999.l.1001.t.2"),
        (b"<player_id>801</player_id>", b"<player_id>999</player_id>"),
        (b"<player_key>999.p.801</player_key>", b""),
        (b'<players count="2">', b'<players count="9">'),
    ],
)
def test_partial_reporting_never_bypasses_required_identity_or_count(
    old: bytes, new: bytes
) -> None:
    with pytest.raises(YahooFantasyError):
        parse(ROSTER.replace(old, new))


@pytest.mark.parametrize(
    "label",
    [
        b"<display_name><synthetic/></display_name>",
        b"<abbreviation>A</abbreviation><abbreviation>B</abbreviation>",
    ],
)
def test_optional_slot_label_failure_does_not_erase_code_and_capacity(
    label: bytes,
) -> None:
    body = SETTINGS.replace(b"<count>1</count>", b"<count>1</count>" + label, 1)
    result = parse_league_settings(body, league_key="999.l.1001")
    original = parse_league_settings(SETTINGS, league_key="999.l.1001")
    assert result.roster_slots == original.roster_slots
    assert result.roster_slots_incomplete
    assert result.scoring is not None and not result.scoring.incomplete


@pytest.mark.parametrize("field", [b"team_key", b"player_key", b"player_id", b"full"])
def test_consumed_identity_attributes_cannot_become_partial_success(
    field: bytes,
) -> None:
    body = ROSTER.replace(
        b"<" + field + b">", b"<" + field + b' synthetic="private-value">', 1
    )
    with pytest.raises(YahooFantasyError):
        parse(body)


@pytest.mark.parametrize("coverage", [b"<date/>", b"<date><synthetic/></date>"])
def test_unknown_selected_coverage_keeps_assigned_code_and_other_players(
    coverage: bytes,
) -> None:
    start = ROSTER.index(b"<selected_position>")
    body = ROSTER[:start] + ROSTER[start:].replace(
        b"<date>2099-10-15</date>", coverage, 1
    )
    result = parse(body)
    assert isinstance(result, Roster) and result.context_unverified
    assert result.entries[0].selected_position == "C"
    assert result.entries[0].selected_coverage is None
    assert result.entries[1].provider_player_id == "999.p.802"


def test_missing_modifier_collection_keeps_categories_without_inventing_weights() -> (
    None
):
    import re

    body = re.sub(rb"<stat_modifiers>.*?</stat_modifiers>", b"", SETTINGS, flags=re.S)
    result = parse_league_settings(body, league_key="999.l.1001")
    assert result.scoring is not None and result.scoring.incomplete
    assert len(result.scoring.rules) == 4
    assert all(rule.modifier is None for rule in result.scoring.rules)
    assert result.roster_slots is not None


@pytest.mark.parametrize("label", [b"<name/>", b"<name><synthetic/></name>"])
def test_stat_presentation_label_failure_preserves_ids_and_modifiers(
    label: bytes,
) -> None:
    body = SETTINGS.replace(b"<name>Invented Goals</name>", label, 1)
    assert body != SETTINGS
    result = parse_league_settings(body, league_key="999.l.1001")
    assert result.scoring is not None and result.scoring.incomplete
    assert len(result.scoring.rules) == 4
    assert result.scoring.rules[0].stat_id == "901"
    assert result.scoring.rules[0].name is None
    assert result.scoring.rules[0].modifier == Decimal(
        "0.12345678901234567890123456789"
    )


def test_malformed_optional_slot_type_preserves_required_code_capacity() -> None:
    body = SETTINGS.replace(
        b"<position_type>P</position_type>",
        b"<position_type><synthetic/></position_type>",
        1,
    )
    result = parse_league_settings(body, league_key="999.l.1001")
    assert result.roster_slots is not None and result.roster_slots_incomplete
    assert (
        result.roster_slots[0].position == "C" and result.roster_slots[0].capacity == 1
    )
    assert result.roster_slots[0].position_type is None
