"""Pure Yahoo settings normalization, shared with the human contract verifier."""

import re
from decimal import Decimal, InvalidOperation
from xml.etree import ElementTree as ET

from fantasy_gm.domain.settings import (
    LeagueSettings,
    RosterSlot,
    ScoringRules,
    StatRule,
    StatScope,
)
from fantasy_gm.providers.yahoo.fantasy import (
    YahooFantasyError,
    _collection,
    _field,
    _flag,
    _known_children,
    _league_game_key,
    _number,
    _one,
    _text,
    _xml_root,
)

# Public YFPY Settings and yfantasy XML models describe these administrative
# scalars. Their values are not used to interpret points or roster assignments.
# https://yfpy.uberfastman.com/models/#yfpy.models.Settings
# https://pkg.go.dev/github.com/famendola1/yfantasy/schema#Settings
_SETTING_METADATA = frozenset(
    {
        "can_trade_draft_picks",
        "cant_cut_list",
        "draft_pick_time",
        "draft_time",
        "draft_together",
        "draft_type",
        "has_playoff_consolation_games",
        "invite_permission",
        "is_auction_draft",
        "max_teams",
        "max_weekly_adds",
        "num_playoff_consolation_teams",
        "num_playoff_teams",
        "persistent_url",
        "pickem_enabled",
        "player_pool",
        "playoff_start_week",
        "post_draft_players",
        "roster_import_deadline",
        "sendbird_channel_url",
        "trade_end_date",
        "trade_ratify_type",
        "trade_reject_time",
        "uses_faab",
        "uses_lock_eliminated_teams",
        "uses_playoff",
        "uses_playoff_reseeding",
        "uses_roster_import",
        "waiver_rule",
        "waiver_time",
        "waiver_type",
    }
)
_COMPETITION_FIELDS = {"has_multiweek_championship", "uses_median_score"}


class YahooSettingsUnsupportedError(YahooFantasyError):
    """Only existing fixed verifier reason codes, never provider values."""

    def __init__(self, reason: str) -> None:
        if reason not in {
            "UNSUPPORTED_SCORING_SETTING",
            "UNSUPPORTED_SCORING_CONTAINER",
            "EMPTY_SCORING_COLLECTION",
            "UNSUPPORTED_STAT_STRUCTURE",
            "UNSUPPORTED_MODIFIER_STRUCTURE",
            "UNSUPPORTED_STRUCTURE",
        }:
            raise ValueError()
        self.reason = reason
        super().__init__("Unsupported Yahoo settings structure")


def _division_metadata(settings: ET.Element, ns: str) -> bool:
    container = _one(settings, "divisions", ns)
    if set(container.attrib) - {"count"} or any(
        c.tag != f"{{{ns}}}division" for c in container
    ):
        return False
    seen: set[str] = set()
    for division in _collection(settings, "divisions", "division", ns):
        if not _known_children(division, {"division_id", "name"}, ns):
            return False
        identity = _text(division, "division_id", ns)
        _number(identity)
        if identity in seen:
            raise ValueError()
        seen.add(identity)
        _text(division, "name", ns)
    return True


def _settings_identity(
    root: ET.Element, ns: str, key: str
) -> tuple[ET.Element, ET.Element, int | None]:
    game = _league_game_key(key)
    league = _one(root, "league", ns)
    if _one(league, "league_key", ns).attrib or _text(league, "league_key", ns) != key:
        raise ValueError()
    for field, expected in (
        ("league_id", key.split(".l.")[1]),
        ("game_key", game),
        ("game_code", "nhl"),
    ):
        if _field(league, field, ns) not in (None, expected):
            raise ValueError()
    settings = _one(league, "settings", ns)
    if any(c.tag.split("}")[-1] == "settings" for c in settings):
        raise ValueError()
    count = _field(league, "num_teams", ns)
    team_count = _number(count) if count is not None else None
    if team_count == 0:
        raise ValueError()
    return league, settings, team_count


def _unsupported_settings(
    settings: ET.Element, ns: str
) -> list[tuple[ET.Element, str, bool]]:
    """Classify only this boundary; unrecognized rules never become harmless."""
    if settings.attrib:
        return [(settings, "Attributes are not supported on settings", True)]
    scalar_rules = {
        "scoring_type",
        "uses_fractional_points",
        "uses_negative_points",
    } | _COMPETITION_FIELDS
    containers = {"stat_categories", "stat_modifiers", "roster_positions"}
    rejected: list[tuple[ET.Element, str, bool]] = []
    seen: set[str] = set()
    for child in settings:
        name = child.tag.split("}")[-1]
        if child.tag == f"{{{ns}}}{name}":
            if name in scalar_rules:
                if not child.attrib:
                    continue  # Consumed scalar/flag validation follows.
            elif name in containers:
                continue
            elif name == "divisions" and _division_metadata(settings, ns):
                continue
            elif name in _SETTING_METADATA and not child.attrib and not len(child):
                if name in seen:
                    raise ValueError()
                seen.add(name)
                continue
        if len(rejected) < 4:
            known = name in scalar_rules | containers | _SETTING_METADATA | {
                "divisions"
            }
            mismatch: list[str] = []
            if child.tag != f"{{{ns}}}{name}":
                mismatch.append("Unexpected namespace")
            if not known:
                mismatch.append("Unrecognized direct field")
            if child.attrib:
                mismatch.append("Attributes are not supported here")
            if name in _SETTING_METADATA and len(child):
                mismatch.append("Administrative field must be scalar")
            rejected.append(
                (
                    child,
                    "; ".join(mismatch) or "Unsupported nested division metadata",
                    known,
                )
            )
    return rejected


def _scoring_structure(
    league: ET.Element,
    settings: ET.Element,
    ns: str,
    *,
    strict: bool = True,
) -> tuple[str, dict[str, ET.Element], dict[str, ET.Element], bool]:
    code = _text(settings, "scoring_type", ns)
    if _field(league, "scoring_type", ns) not in (None, code):
        raise ValueError()
    categories = _one(settings, "stat_categories", ns)
    modifiers = (
        _one(settings, "stat_modifiers", ns)
        if strict or any(c.tag.split("}")[-1] == "stat_modifiers" for c in settings)
        else None
    )
    incomplete = modifiers is None or not all(
        _known_children(node, {"stats"}, ns)
        for node in (categories, modifiers)
        if node is not None
    )
    if incomplete and strict:
        raise YahooSettingsUnsupportedError("UNSUPPORTED_SCORING_CONTAINER")
    category_items = _collection(categories, "stats", "stat", ns)
    modifier_items = (
        _collection(modifiers, "stats", "stat", ns) if modifiers is not None else []
    )
    if not category_items or not modifier_items:
        if strict:
            raise YahooSettingsUnsupportedError("EMPTY_SCORING_COLLECTION")
        incomplete = True
    stats: dict[str, ET.Element] = {}
    for item in category_items:
        if not _known_children(
            item,
            {
                "stat_id",
                "enabled",
                "name",
                "display_name",
                "sort_order",
                "position_type",
                "stat_position_types",
                "is_only_display_stat",
                "is_excluded_from_display",
            },
            ns,
        ):
            if strict:
                raise YahooSettingsUnsupportedError("UNSUPPORTED_STAT_STRUCTURE")
            incomplete = True
        if _one(item, "stat_id", ns).attrib:
            raise ValueError()
        stat_id = _text(item, "stat_id", ns)
        _number(stat_id)
        if stat_id in stats:
            raise ValueError()
        stats[stat_id] = item
    by_id: dict[str, ET.Element] = {}
    for item in modifier_items:
        if not _known_children(item, {"stat_id", "value"}, ns):
            if strict:
                raise YahooSettingsUnsupportedError("UNSUPPORTED_MODIFIER_STRUCTURE")
            incomplete = True
        if _one(item, "stat_id", ns).attrib:
            raise ValueError()
        stat_id = _text(item, "stat_id", ns)
        if stat_id not in stats or stat_id in by_id:
            raise ValueError()
        by_id[stat_id] = item
    return code, stats, by_id, incomplete


def _modifiers(items: dict[str, ET.Element], ns: str) -> dict[str, Decimal]:
    weights: dict[str, Decimal] = {}
    for stat_id, item in items.items():
        if _one(item, "value", ns).attrib:
            raise ValueError()
        value = _text(item, "value", ns)
        if len(value) > 80:
            raise ValueError()
        try:
            weight = Decimal(value)
        except InvalidOperation:
            raise ValueError() from None
        if not weight.is_finite():
            raise ValueError()
        if not re.fullmatch(r"[+-]?[0-9]+(?:\.[0-9]+)?", value):
            raise YahooSettingsUnsupportedError("UNSUPPORTED_STRUCTURE")
        weights[stat_id] = weight
    return weights


def _bool_field(node: ET.Element, name: str, ns: str) -> bool | None:
    if any(c.tag.split("}")[-1] == name for c in node):
        if _one(node, name, ns).attrib:
            raise YahooSettingsUnsupportedError("UNSUPPORTED_STRUCTURE")
    value = _flag(node, name, ns)
    if value is None and any(c.tag.split("}")[-1] == name for c in node):
        raise ValueError()  # Empty is not absence and cannot silently default.
    return None if value is None else value == "1"


def _stat_rules(
    stats: dict[str, ET.Element],
    weights: dict[str, Decimal],
    ns: str,
    *,
    strict: bool = True,
) -> tuple[StatRule, ...]:
    rules = []
    for stat_id, item in stats.items():
        incomplete = False
        label = None
        if strict:
            label = _field(item, "name", ns) or _field(item, "display_name", ns)
            if not label or not label.strip():
                raise YahooSettingsUnsupportedError("UNSUPPORTED_STRUCTURE")
        else:
            for field in ("name", "display_name"):
                try:
                    candidate = _field(item, field, ns)
                    if candidate is not None and not candidate.strip():
                        raise ValueError()
                    if candidate:
                        label = candidate
                        break
                except ValueError:
                    incomplete = True
            if label is None:
                incomplete = True
        scopes: tuple[StatScope, ...] | None = None
        flags: dict[str, bool | None] = {}
        for field in ("enabled", "is_only_display_stat", "is_excluded_from_display"):
            try:
                flags[field] = _bool_field(item, field, ns)
            except (ValueError, YahooSettingsUnsupportedError):
                if strict:
                    raise
                flags[field] = None
                incomplete = True
        try:
            position_type = _field(item, "position_type", ns)
            if (
                any(c.tag.split("}")[-1] == "position_type" for c in item)
                and _one(item, "position_type", ns).attrib
            ):
                raise ValueError()
        except ValueError:
            if strict:
                raise
            position_type = None
            incomplete = True
        try:
            scopes = _stat_scopes(item, ns)
        except (ValueError, YahooSettingsUnsupportedError):
            if strict:
                raise
            incomplete = True
        rules.append(
            StatRule(
                stat_id=stat_id,
                name=label,
                modifier=weights.get(stat_id),
                enabled=flags["enabled"],
                display_only=flags["is_only_display_stat"],
                excluded_from_display=flags["is_excluded_from_display"],
                position_type=position_type,
                scopes=scopes,
                incomplete=incomplete,
            )
        )
    return tuple(rules)


def _stat_scopes(item: ET.Element, ns: str) -> tuple[StatScope, ...] | None:
    if any(c.tag.split("}")[-1] == "stat_position_types" for c in item):
        values = []
        for scope in _collection(item, "stat_position_types", "stat_position_type", ns):
            if not _known_children(
                scope, {"position_type", "is_only_display_stat"}, ns
            ):
                raise YahooSettingsUnsupportedError("UNSUPPORTED_STRUCTURE")
            values.append(
                StatScope(
                    position_type=_text(scope, "position_type", ns),
                    display_only=_bool_field(scope, "is_only_display_stat", ns),
                )
            )
        if len({s.position_type for s in values}) != len(values):
            raise ValueError()
        return tuple(values)
    return None


def _slots(
    settings: ET.Element, ns: str, *, strict: bool = True
) -> tuple[tuple[RosterSlot, ...], bool]:
    container = _one(settings, "roster_positions", ns)
    incomplete = bool(set(container.attrib) - {"count"})
    if incomplete and strict:
        raise YahooSettingsUnsupportedError("UNSUPPORTED_STRUCTURE")
    slots: list[RosterSlot] = []
    for slot in _collection(settings, "roster_positions", "roster_position", ns):
        # Published yfantasy XML types include these optional presentation labels:
        # https://pkg.go.dev/github.com/famendola1/yfantasy/schema#RosterPosition
        # Consume the code/capacity/type; no aliases or bench mappings are inferred.
        if not _known_children(
            slot,
            {"position", "position_type", "count", "abbreviation", "display_name"},
            ns,
        ):
            if strict:
                raise YahooSettingsUnsupportedError("UNSUPPORTED_STRUCTURE")
            incomplete = True
        for field in ("position", "count"):
            if (
                any(c.tag.split("}")[-1] == field for c in slot)
                and _one(slot, field, ns).attrib
            ):
                raise ValueError()
        for label in ("abbreviation", "display_name"):
            try:
                _field(slot, label, ns)  # Labels cannot invalidate slot facts.
            except ValueError:
                if strict:
                    raise
                incomplete = True
        try:
            position_type = _field(slot, "position_type", ns)
            if (
                any(c.tag.split("}")[-1] == "position_type" for c in slot)
                and _one(slot, "position_type", ns).attrib
            ):
                raise ValueError()
        except ValueError:
            if strict:
                raise
            position_type = None
            incomplete = True
        slots.append(
            RosterSlot(
                position=_text(slot, "position", ns),
                capacity=_number(_text(slot, "count", ns)),
                position_type=position_type,
            )
        )
    if not slots or len({s.position for s in slots}) != len(slots):
        raise ValueError()
    return tuple(slots), incomplete


def parse_league_settings(content: bytes, *, league_key: str) -> LeagueSettings:
    """Return validated observations; unsupported meaning cannot erase them."""
    try:
        root, ns = _xml_root(content)
        league, settings, _ = _settings_identity(root, ns, league_key)
    except (ValueError, YahooFantasyError):
        raise YahooFantasyError("Malformed Yahoo settings identity") from None
    incomplete = False
    try:
        incomplete = bool(_unsupported_settings(settings, ns))
    except (ValueError, YahooSettingsUnsupportedError):
        incomplete = True
    flags: dict[str, bool | None] = {}
    for field in (
        "has_multiweek_championship",
        "uses_median_score",
        "uses_fractional_points",
        "uses_negative_points",
    ):
        try:
            flags[field] = _bool_field(settings, field, ns)
        except (ValueError, YahooSettingsUnsupportedError):
            flags[field] = None
            incomplete = True
    scoring = None
    try:
        code, stats, modifiers, structure_incomplete = _scoring_structure(
            league,
            settings,
            ns,
            strict=False,
        )
        weights: dict[str, Decimal] = {}
        for stat_id, item in modifiers.items():
            try:
                weights.update(_modifiers({stat_id: item}, ns))
            except (ValueError, YahooSettingsUnsupportedError):
                incomplete = True  # That weight remains absent, never zero.
        rules = _stat_rules(stats, weights, ns, strict=False)
        incomplete |= structure_incomplete or any(
            r.incomplete
            or (
                r.modifier is None
                and r.display_only is not True
                and r.enabled is not False
            )
            for r in rules
        )
        scoring = ScoringRules(
            format_code=code,
            fractional_points=flags["uses_fractional_points"],
            negative_points=flags["uses_negative_points"],
            rules=rules,
            incomplete=incomplete,
        )
    except (ValueError, YahooSettingsUnsupportedError):
        pass  # Ambiguous required stat identity/join/hierarchy: no safe table.
    slots = None
    slots_incomplete = True
    try:
        slots, slots_incomplete = _slots(settings, ns, strict=False)
    except (ValueError, YahooSettingsUnsupportedError):
        pass
    return LeagueSettings(
        provider="yahoo",
        provider_league_id=league_key,
        scoring=scoring,
        roster_slots=slots,
        roster_slots_incomplete=slots_incomplete,
        multiweek_championship=flags["has_multiweek_championship"],
        median_matchup=flags["uses_median_score"],
    )
