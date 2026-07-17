import pytest

from src.common.config import Settings, get_settings


def test_settings_initialization() -> None:
    settings = get_settings()
    assert settings.ENV in ["development", "production", "test"]
    assert (
        "postgresql://" in settings.POSTGRES_URL or "postgresql+asyncpg://" in settings.POSTGRES_URL
    )


def test_settings_validation_invalid_postgres() -> None:
    with pytest.raises(
        ValueError, match="POSTGRES_URL must be a valid PostgreSQL connection string"
    ):
        Settings(POSTGRES_URL="mysql://localhost:3306/db")


def test_settings_validation_invalid_redis() -> None:
    with pytest.raises(ValueError, match="REDIS_URL must be a valid Redis connection string"):
        Settings(REDIS_URL="mongodb://localhost:27017/db")
