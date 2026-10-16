"""Reported league configuration, without scoring calculations or defaults."""

from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from fantasy_gm.domain.league import NonEmptyString
from fantasy_gm.domain.roster import PositionCode


class StatScope(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    position_type: PositionCode
    display_only: bool | None = None


class StatRule(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    stat_id: NonEmptyString
    name: NonEmptyString | None
    modifier: Decimal | None
    # Validated provider text; Decimal preserves value, not lexical spelling.
    modifier_literal: NonEmptyString | None = None
    enabled: bool | None = None
    display_only: bool | None = None
    excluded_from_display: bool | None = None
    position_type: str | None = None
    scopes: tuple[StatScope, ...] | None = None
    incomplete: bool = False


class ScoringRules(BaseModel):
    """Exact reported modifiers/flags; format_code is opaque, never translated."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    format_code: Annotated[str, StringConstraints(min_length=1)]
    fractional_points: bool | None
    negative_points: bool | None
    rules: tuple[StatRule, ...]
    # Reported fields can be useful without a complete scoring contract.
    incomplete: bool = True


class RosterSlot(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    position: PositionCode
    capacity: int = Field(ge=0)
    position_type: str | None = None


class LeagueSettings(BaseModel):
    """Independent optional sections; None means unavailable, never an empty set."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    provider: NonEmptyString
    provider_league_id: NonEmptyString
    scoring: ScoringRules | None
    roster_slots: tuple[RosterSlot, ...] | None
    roster_slots_incomplete: bool = True
    multiweek_championship: bool | None = None
    median_matchup: bool | None = None
