from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="VMF_",
        env_file_encoding="utf-8",
        extra="ignore",
        populate_by_name=True,
    )

    app_name: str = "VMF Fantasy API"
    environment: Literal["development", "test", "staging", "production"] = "development"
    api_prefix: str = "/api"
    database_url: str = "postgresql+psycopg://vmf:vmf@localhost:5432/vmf"
    migration_database_url: str | None = None
    sql_echo: bool = False
    database_use_null_pool: bool = False
    database_disable_prepared_statements: bool = False
    admin_api_key: SecretStr | None = Field(default=None, min_length=32)
    cron_secret: SecretStr | None = Field(
        default=None,
        min_length=32,
        validation_alias=AliasChoices("VMF_CRON_SECRET", "CRON_SECRET"),
    )
    cors_origins: list[str] = Field(default_factory=lambda: ["http://localhost:3000"])

    fpl_base_url: str = "https://fantasy.premierleague.com/api"
    fpl_timeout_seconds: float = 15.0
    fpl_user_agent: str = "VMF-Fantasy-League/0.1"
    fpl_max_attempts: int = 3
    fpl_retry_base_delay_seconds: float = 1.0
    fpl_max_concurrency: int = 4
    fpl_response_max_bytes: int = 16 * 1024 * 1024

    active_season_code: str = "2026/27"
    #: Managers processed per cron invocation. Keeping the batch small leaves
    #: headroom under the serverless execution limit of the free plan.
    sync_manager_batch_size: int = 10

    number_of_managers: int = 40
    division_size: int = 20
    promotion_count: int = 6
    relegation_count: int = 6
    maximum_allowed_transfer_cost: int = 8
    h2h_violation_deduction: int = 6
    refresh_interval_seconds: int = 60

    @field_validator("admin_api_key", "cron_secret", mode="before")
    @classmethod
    def blank_secret_as_none(cls, value: object) -> object:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @field_validator("database_url", "migration_database_url")
    @classmethod
    def normalize_postgres_driver(cls, value: str | None) -> str | None:
        """Accept connection strings copied from Supabase's Connect panel.

        The application and Alembic use psycopg 3's async implementation, while
        Supabase presents a generic ``postgresql://`` URL.
        """

        if value is None:
            return None
        if value.startswith("postgres://"):
            return value.replace("postgres://", "postgresql+psycopg://", 1)
        if value.startswith("postgresql://"):
            return value.replace("postgresql://", "postgresql+psycopg://", 1)
        return value

    @property
    def effective_migration_database_url(self) -> str:
        """Use the migration connection when configured, otherwise local DB URL."""

        return self.migration_database_url or self.database_url


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
