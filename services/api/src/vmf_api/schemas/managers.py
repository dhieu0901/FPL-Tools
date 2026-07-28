from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, HttpUrl

from vmf_api.models.enums import Division, ManagerStatus, RegistrationStatus
from vmf_api.schemas.common import ORMModel


class ManagerCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    fpl_entry_id: int = Field(gt=0)
    manager_name: str = Field(min_length=1, max_length=120)
    team_name: str = Field(min_length=1, max_length=120)
    phone_number: str | None = Field(default=None, max_length=32)
    facebook_url: HttpUrl | None = None
    division: Division
    season_joined: str = Field(min_length=4, max_length=16)
    registration_status: RegistrationStatus = RegistrationStatus.PENDING


class ManagerUpdate(BaseModel):
    """Mutable fields only; registered manager/team names are intentionally absent."""

    division: Division | None = None
    active_status: ManagerStatus | None = None
    registration_status: RegistrationStatus | None = None
    season_2_league_joined: bool | None = None
    season_2_join_gameweek: int | None = Field(default=None, ge=20, le=38)
    locked_from_gameweek: int | None = Field(default=None, ge=1, le=38)


class ManagerPublic(ORMModel):
    id: int
    fpl_entry_id: int
    manager_name: str
    team_name: str
    division: Division
    active_status: ManagerStatus
    registration_status: RegistrationStatus
    season_joined: str
    season_2_league_joined: bool
    season_2_join_gameweek: int | None
    created_at: datetime
    updated_at: datetime


class ManagerAdmin(ManagerPublic):
    phone_number: str | None
    facebook_url: str | None
    locked_from_gameweek: int | None
    join_violation_applied: bool
