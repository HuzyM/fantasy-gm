"""Supplied daily-skater assumptions, independent of reported provider fields."""

from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from fantasy_gm.domain.league import NonEmptyString

SkaterPosition = Literal["C", "LW", "RW", "D", "F", "W", "UTIL"]


class SkaterProjection(BaseModel):
    """Caller-supplied points and exact allowed slots; no eligibility inference."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    player_id: NonEmptyString
    projected_points: Decimal = Field(allow_inf_nan=False)
    eligible_positions: tuple[SkaterPosition, ...] = Field(min_length=1)


class SlotCapacity(BaseModel):
    """Maximum starters of one type; unfilled slots contribute zero points."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    position: SkaterPosition
    capacity: int = Field(ge=0)


class LineupAssignment(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    player_id: NonEmptyString
    position: SkaterPosition


class LineupChange(BaseModel):
    """A changed skater's assignment, not a transaction or prediction."""

    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    player_id: str
    from_position: SkaterPosition | None
    to_position: SkaterPosition | None
    projected_points: Decimal
    reason: str


class DailyLineupResult(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, extra="forbid")
    assignments: tuple[LineupAssignment, ...]
    benched_player_ids: tuple[str, ...]
    projected_points: Decimal
    baseline_points: Decimal
    estimated_improvement: Decimal
    changes: tuple[LineupChange, ...]
