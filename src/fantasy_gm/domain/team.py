"""Minimal provider-independent team identity, held only in memory."""

from pydantic import BaseModel, ConfigDict

from fantasy_gm.domain.league import NonEmptyString


class Team(BaseModel):
    """Identity only; no managers, account data, roster, or scoring payload."""

    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    provider: NonEmptyString
    provider_league_id: NonEmptyString
    provider_team_id: NonEmptyString
    name: NonEmptyString
