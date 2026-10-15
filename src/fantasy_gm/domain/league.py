"""Minimal provider-independent league identity, used only in memory."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

NonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class League(BaseModel):
    """No roster, scoring, user profile, or provider transport payload."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    provider: NonEmptyString
    provider_league_id: NonEmptyString
    name: NonEmptyString
    sport: NonEmptyString | None = None
    season: Annotated[int, Field(gt=0)] | None = None
