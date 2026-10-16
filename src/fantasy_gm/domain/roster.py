"""Reported roster facts only; no lineup legality or completeness inference."""

from datetime import date as Date
from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from fantasy_gm.domain.league import NonEmptyString
from fantasy_gm.domain.team import Team

PositionCode = Annotated[str, StringConstraints(min_length=1)]


class RosterCoverage(BaseModel):
    """Preserve the reported kind/week, including unfamiliar opaque values."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    kind: str | None = None
    date: Date | None = None
    week: str | None = None


class RosterEntry(BaseModel):
    """Opaque position codes represent returned fields, not position legality."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    provider_player_id: NonEmptyString
    name: NonEmptyString
    eligible_positions: tuple[PositionCode, ...] | None = None
    selected_position: PositionCode | None = None
    selected_coverage: RosterCoverage | None = None
    selected_is_flex: bool | None = None
    # Reported professional affiliation, not a current-team/appearance guarantee.
    professional_team_code: (
        Annotated[str, StringConstraints(pattern=r"^[A-Z]{2,3}$")] | None
    ) = None
    professional_team_unverified: bool = False


class Roster(BaseModel):
    """One in-memory response; returned_count is not total completeness proof."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    team: Team
    entries: tuple[RosterEntry, ...]
    coverage: RosterCoverage
    returned_count: int | None
    # This slice makes only unparameterized GETs; never fill this from the clock.
    requested_date: Date | None = None
    # A reported provider state may have verified syntax but unresolved meaning.
    # No effective/current coverage, legality or completeness follows from it.
    context_unverified: bool = False
