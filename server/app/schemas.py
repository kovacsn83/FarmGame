from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator


PLAYER_NAME_MAX_LENGTH = 24
VERSION_PATTERN = r"^\d+\.\d+\.\d+(?:[-+][0-9A-Za-z.-]+)?$"


class ChallengeSubmission(BaseModel):
    model_config = ConfigDict(extra="forbid")

    player_id: UUID
    player_name: Annotated[str, Field(min_length=1, max_length=PLAYER_NAME_MAX_LENGTH)]
    game_id: UUID
    game_version: Annotated[str, Field(min_length=1, max_length=40, pattern=VERSION_PATTERN)]
    farm_value: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    challenge_years: Annotated[int, Field(strict=True)]
    completed_at: datetime

    @field_validator("player_name", mode="before")
    @classmethod
    def normalize_player_name(cls, value):
        if not isinstance(value, str):
            return value
        normalized = value.strip()
        if not normalized:
            raise ValueError("player_name must not be blank")
        return normalized

    @field_validator("completed_at")
    @classmethod
    def require_timezone(cls, value):
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("completed_at must include a timezone")
        return value

    @field_validator("challenge_years")
    @classmethod
    def require_ten_years(cls, value):
        if value != 10:
            raise ValueError("challenge_years must be 10")
        return value


class SubmissionResponse(BaseModel):
    status: str
    result_id: int
    game_id: str
    farm_value: float
    rank: int


class LeaderboardEntry(BaseModel):
    rank: int
    player_name: str
    farm_value: float
    game_version: str
    completed_at: datetime


class LeaderboardResponse(BaseModel):
    challenge: str
    challenge_years: int
    results: list[LeaderboardEntry]
