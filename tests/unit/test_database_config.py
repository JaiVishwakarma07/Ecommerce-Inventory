from pathlib import Path

import pytest
from pydantic import ValidationError


def test_resolved_database_url_uses_file_sqlite_in_development():
    from app.config import Settings

    settings = Settings(
        app_env="development",
        sqlite_dev_db_path="./data/ecom_oppo.db",
        database_url="",
    )

    expected_url = f"sqlite+aiosqlite:///{Path('./data/ecom_oppo.db').as_posix()}"
    assert settings.resolved_database_url == expected_url


def test_resolved_database_url_uses_memory_sqlite_in_test_env():
    from app.config import Settings

    settings = Settings(
        app_env="test",
        sqlite_dev_db_path="./data/ecom_oppo.db",
        database_url="",
    )

    assert settings.resolved_database_url == "sqlite+aiosqlite:///:memory:"


def test_for_test_overrides_database_url_with_memory_default():
    from app.config import Settings

    settings = Settings.for_test()

    assert settings.app_env == "test"
    assert settings.resolved_database_url == "sqlite+aiosqlite:///:memory:"


def test_validate_secret_raises_in_staging_with_default_key():
    from app.config import Settings

    with pytest.raises(ValidationError):
        Settings(
            app_env="staging",
            jwt_secret_key="dev-secret-change-me",
            sqlite_dev_db_path="./data/ecom_oppo.db",
            database_url="",
        )


def test_validate_secret_passes_in_staging_with_real_key():
    from app.config import Settings

    settings = Settings(
        app_env="staging",
        jwt_secret_key="a-real-strong-secret",
        sqlite_dev_db_path="./data/ecom_oppo.db",
        database_url="",
    )
    assert settings.app_env == "staging"
