"""Tests for src.common.config."""

import pytest

from src.common.config import Settings, get_settings


def test_settings_default_postgres_url() -> None:
    settings = Settings()
    assert settings.postgres_url.startswith("postgresql://")


def test_settings_reads_postgres_url_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("POSTGRES_URL", "postgresql://user:pw@example.com/db")
    settings = Settings()
    assert settings.postgres_url == "postgresql://user:pw@example.com/db"


def test_get_settings_is_cached() -> None:
    get_settings.cache_clear()
    assert get_settings() is get_settings()
    get_settings.cache_clear()
