import pytest
from pydantic import ValidationError

from vmf_api.core.config import Settings


def test_settings_accept_supabase_connection_strings_and_separate_migration_url() -> None:
    settings = Settings(
        _env_file=None,
        database_url="postgres://runtime:secret@pooler.example:6543/postgres",
        migration_database_url=("postgresql://migrations:secret@pooler.example:5432/postgres"),
    )

    assert settings.database_url.startswith("postgresql+psycopg://runtime:")
    assert settings.effective_migration_database_url.startswith("postgresql+psycopg://migrations:")


def test_settings_falls_back_to_runtime_url_for_local_migrations() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite:///:memory:",
    )

    assert settings.effective_migration_database_url == settings.database_url


def test_cron_secret_accepts_vercel_native_environment_name(monkeypatch) -> None:
    monkeypatch.setenv("CRON_SECRET", "vercel-generated-secret-at-least-32")

    settings = Settings(_env_file=None)

    assert settings.cron_secret is not None
    assert settings.cron_secret.get_secret_value() == "vercel-generated-secret-at-least-32"


def test_blank_optional_secrets_are_treated_as_unconfigured() -> None:
    settings = Settings(_env_file=None, admin_api_key="", cron_secret="")

    assert settings.admin_api_key is None
    assert settings.cron_secret is None


@pytest.mark.parametrize("field", ["admin_api_key", "cron_secret"])
def test_configured_secrets_must_be_at_least_32_characters(field: str) -> None:
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **{field: "too-short"})


def test_manager_batch_reads_the_whole_league_by_default() -> None:
    """Nobody may be left holding a part-played score because a batch ran out."""

    settings = Settings(_env_file=None, database_url="sqlite+aiosqlite:///:memory:")

    assert settings.sync_manager_batch_size is None


@pytest.mark.parametrize("value", ["", "  ", 0, -5, "0"])
def test_a_blank_or_non_positive_batch_means_no_limit_not_nobody(value: object) -> None:
    """A zero would slice the batch down to nobody and freeze every score."""

    settings = Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite:///:memory:",
        sync_manager_batch_size=value,
    )

    assert settings.sync_manager_batch_size is None


def test_an_explicit_batch_is_still_honoured() -> None:
    settings = Settings(
        _env_file=None,
        database_url="sqlite+aiosqlite:///:memory:",
        sync_manager_batch_size=10,
    )

    assert settings.sync_manager_batch_size == 10
