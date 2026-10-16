"""Immutable public-sports observations; independent of Yahoo and HTTP."""

from datetime import date, datetime, timedelta
from enum import StrEnum
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

Identity = Annotated[str, StringConstraints(min_length=1, max_length=64)]
Code = Annotated[str, StringConstraints(min_length=1, max_length=32)]
Season = Annotated[str, StringConstraints(pattern=r"^[0-9]{8}$")]


class GameType(StrEnum):
    EXHIBITION = "EXHIBITION"
    REGULAR = "REGULAR"
    POSTSEASON = "POSTSEASON"
    UNKNOWN = "UNKNOWN"


class GameState(StrEnum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    POSTPONED = "POSTPONED"
    CANCELLED = "CANCELLED"
    RESCHEDULED = "RESCHEDULED"
    UNKNOWN = "UNKNOWN"


class ScheduleTeam(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    provider: Identity
    provider_team_id: Identity
    abbreviation: Annotated[str, StringConstraints(pattern=r"^[A-Z]{3}$")]
    name: Annotated[str, StringConstraints(max_length=256)] | None = None


class ScheduledGame(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    provider_game_id: Identity
    season: Season
    game_type: GameType
    game_type_code: Code
    home: ScheduleTeam
    away: ScheduleTeam
    reported_date: date
    start_time_utc: datetime | None
    state: GameState
    state_code: Code | None
    schedule_state_code: Code | None
    schedule_normal: bool

    @model_validator(mode="after")
    def validate_identity_and_time(self) -> Self:
        if (
            self.home.provider != self.away.provider
            or self.home.provider_team_id == self.away.provider_team_id
            or self.home.abbreviation == self.away.abbreviation
            or int(self.season[4:]) != int(self.season[:4]) + 1
        ):
            raise ValueError("INVALID_IDENTITY")
        if self.start_time_utc is not None and (
            self.start_time_utc.tzinfo is None
            or self.start_time_utc.utcoffset() != timedelta(0)
        ):
            raise ValueError("UTC_REQUIRED")
        return self


class ScheduleSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    season: Season
    teams: tuple[ScheduleTeam, ...]
    games: tuple[ScheduledGame, ...]
    # These dates have meaning only in coverage_timezone and a qualified profile.
    covered_dates: frozenset[date]
    coverage_timezone: str | None = None
    cohort_verified: bool
    coverage_contract_verified: bool
    issues: tuple[str, ...]
    observed_at_utc: datetime

    @model_validator(mode="after")
    def validate_consistency(self) -> Self:
        if (
            int(self.season[4:]) != int(self.season[:4]) + 1
            or self.observed_at_utc.tzinfo is None
            or self.observed_at_utc.utcoffset() != timedelta(0)
        ):
            raise ValueError("INVALID_CONTEXT")
        by_id = {team.provider_team_id: team for team in self.teams}
        if len(by_id) != len(self.teams) or len(
            {team.abbreviation for team in self.teams}
        ) != len(self.teams):
            raise ValueError("INVALID_IDENTITY")
        seen: dict[str, ScheduledGame] = {}
        for game in self.games:
            if game.season != self.season:
                raise ValueError("INVALID_CONTEXT")
            for team in (game.home, game.away):
                if by_id.get(team.provider_team_id) != team:
                    raise ValueError("INVALID_IDENTITY")
            if game.provider_game_id in seen and seen[game.provider_game_id] != game:
                raise ValueError("CONFLICTING_GAME")
            seen[game.provider_game_id] = game
        return self


class TeamScheduleSummary(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    team: ScheduleTeam
    scheduled: int = Field(ge=0)
    in_progress: int = Field(ge=0)
    completed: int = Field(ge=0)
    uncertain_dated: int = Field(ge=0)
    unplaced: int = Field(ge=0)
    games: tuple[ScheduledGame, ...]
    back_to_back_pairs: tuple[tuple[str, str], ...]
    count_complete: bool
    back_to_back_complete: bool

    @property
    def total(self) -> int:
        return self.scheduled + self.in_progress + self.completed


class ScheduleReport(BaseModel):
    model_config = ConfigDict(frozen=True, strict=True, hide_input_in_errors=True)
    summaries: tuple[TeamScheduleSummary, ...]
    ranking_available: bool
    issues: tuple[str, ...]

    @property
    def most_games(self) -> tuple[str, ...]:
        if not self.ranking_available or not self.summaries:
            return ()
        maximum = max(item.total for item in self.summaries)
        return tuple(s.team.abbreviation for s in self.summaries if s.total == maximum)

    @property
    def fewest_games(self) -> tuple[str, ...]:
        if not self.ranking_available or not self.summaries:
            return ()
        minimum = min(item.total for item in self.summaries)
        return tuple(s.team.abbreviation for s in self.summaries if s.total == minimum)
