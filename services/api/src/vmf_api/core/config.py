from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VMF_",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "VMF Fantasy API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+asyncpg://vmf:vmf@localhost:5432/vmf"
    sql_echo: bool = False
    admin_api_key: SecretStr | None = None
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    fpl_timeout_seconds: float = 15.0
    fpl_user_agent: str = "VMF-Fantasy-League/0.1"

    number_of_managers: int = 40
    division_size: int = 20
    promotion_count: int = 6
    relegation_count: int = 6
    maximum_allowed_transfer_cost: int = 8
    h2h_violation_deduction: int = 6
    refresh_interval_seconds: int = 60


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
