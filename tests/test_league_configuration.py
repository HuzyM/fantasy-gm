"""Configuration normalization from invented XML only."""

from decimal import Decimal

import pytest

from tests.test_yahoo_contract_verifier import SETTINGS


def test_reported_configuration_keeps_exact_modifiers_and_display_scopes() -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    result = parse_league_settings(SETTINGS, league_key="999.l.1001")
    assert result.scoring is not None and result.roster_slots is not None
    rules = {rule.stat_id: rule for rule in result.scoring.rules}
    assert rules["901"].modifier == Decimal("0.12345678901234567890123456789")
    assert rules["902"].modifier == Decimal("-2.50")
    assert rules["903"].modifier == Decimal("0")
    assert rules["904"].modifier is None and rules["904"].display_only is True
    assert rules["901"].scopes is not None
    assert rules["901"].scopes[1].display_only is True
    assert result.scoring.fractional_points is True
    assert result.multiweek_championship is None and result.median_matchup is None


@pytest.mark.parametrize("value", ["0", "1"])
def test_documented_competition_options_are_preserved_not_added_to_weights(
    value: str,
) -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    body = SETTINGS.replace(
        b"</settings>",
        (
            f"<has_multiweek_championship>{value}</has_multiweek_championship>"
            f"<uses_median_score>{value}</uses_median_score></settings>"
        ).encode(),
    )
    result = parse_league_settings(body, league_key="999.l.1001")
    assert result.multiweek_championship is (value == "1")
    assert result.median_matchup is (value == "1")
    assert result.scoring is not None and len(result.scoring.rules) == 4
    from tests.test_yahoo_contract_verifier import PAYLOADS, lines, run_fake

    payloads = PAYLOADS.copy()
    payloads[1] = body
    report, _, private = run_fake(payloads)
    assert "SCORING_STRUCTURE PASS" in lines(report)
    assert f"uses_median_score='{value}'" in "\n".join(private)
    assert f"has_multiweek_championship='{value}'" in "\n".join(private)


@pytest.mark.parametrize(
    "extension",
    [
        b"<league_premium_features/>",
        b"<synthetic_bonus/>",
        b"<uses_median_score>2</uses_median_score>",
    ],
)
def test_unknown_or_invalid_rules_leave_partial_scoring_and_independent_slots(
    extension: bytes,
) -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    result = parse_league_settings(
        SETTINGS.replace(b"</settings>", extension + b"</settings>"),
        league_key="999.l.1001",
    )
    assert result.scoring is not None and result.scoring.incomplete
    assert result.roster_slots is not None and not result.roster_slots_incomplete


@pytest.mark.parametrize(
    "old,new",
    [
        (b"<value>-2.50</value>", b""),
        (b"<stat_id>902</stat_id><value>", b"<stat_id>99999</stat_id><value>"),
        (b"<value>-2.50</value>", b"<value>NaN</value>"),
        (b"<value>-2.50</value>", b"<value>1e5</value>"),
        (
            b"<is_only_display_stat>1</is_only_display_stat></stat>\n</stats>",
            b"</stat>\n</stats>",
        ),
    ],
)
def test_invalid_or_incomplete_scoring_never_becomes_complete(
    old: bytes, new: bytes
) -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    assert old in SETTINGS
    result = parse_league_settings(SETTINGS.replace(old, new), league_key="999.l.1001")
    if b"99999" in new:  # A broken join cannot produce a trustworthy table.
        assert result.scoring is None
    else:
        assert result.scoring is not None and result.scoring.incomplete
        assert result.scoring.rules[0].modifier is not None


@pytest.mark.parametrize("key", ["999.l.1002", "998.l.1001"])
def test_wrong_league_settings_are_fatal_not_optional(key: str) -> None:
    from fantasy_gm.providers.yahoo.fantasy import YahooFantasyError
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    with pytest.raises(YahooFantasyError):
        parse_league_settings(SETTINGS, league_key=key)


def test_documented_slot_labels_do_not_change_opaque_codes_or_capacity() -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    body = SETTINGS.replace(
        b"<count>1</count>",
        b"<count>1</count><abbreviation>Invented</abbreviation>"
        b"<display_name>Invented Label</display_name>",
    )
    result = parse_league_settings(body, league_key="999.l.1001")
    original = parse_league_settings(SETTINGS, league_key="999.l.1001")
    assert result.roster_slots == original.roster_slots and result.scoring is not None


def test_unknown_slot_rules_are_separate_from_reported_scoring() -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    body = SETTINGS.replace(
        b"<roster_positions>", b'<roster_positions synthetic="private">'
    )
    result = parse_league_settings(body, league_key="999.l.1001")
    assert result.roster_slots is not None and result.roster_slots_incomplete
    assert result.scoring is not None and not result.scoring.incomplete


def test_visibility_flag_is_not_a_display_only_scoring_rule() -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    body = SETTINGS.replace(
        b"<name>Invented Display</name>\n<is_only_display_stat>1",
        b"<name>Invented Display</name>\n<is_excluded_from_display>1",
    ).replace(
        b"</is_only_display_stat></stat>\n</stats>",
        b"</is_excluded_from_display></stat>\n</stats>",
    )
    assert body != SETTINGS
    scoring = parse_league_settings(body, league_key="999.l.1001").scoring
    assert scoring is not None and scoring.incomplete
    assert scoring.rules[3].modifier is None
    assert scoring.rules[3].display_only is None
    assert scoring.rules[3].excluded_from_display is True


def test_format_and_scope_codes_are_preserved_without_trimming_or_mapping() -> None:
    from fantasy_gm.providers.yahoo.settings import parse_league_settings

    body = SETTINGS.replace(b"invented-points", b" UNMAPPED FORMAT ").replace(
        b"<position_type>P</position_type>", b"<position_type> P </position_type>"
    )
    scoring = parse_league_settings(body, league_key="999.l.1001").scoring
    assert scoring is not None and scoring.format_code == " UNMAPPED FORMAT "
    assert scoring.rules[0].position_type == " P "
    assert scoring.rules[0].scopes is not None
    assert scoring.rules[0].scopes[0].position_type == " P "
