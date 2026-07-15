"""Application settings loaded from environment variables."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration sourced from the environment / .env file."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    postgres_url: str = "postgresql://creditlens:devpassword@localhost:5432/creditlens"


@lru_cache
def get_settings() -> Settings:
    """Return a cached Settings instance."""
    return Settings()
