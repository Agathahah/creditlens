"""Tests for src.common.database."""

from unittest.mock import MagicMock

import pytest
from sqlalchemy.orm import DeclarativeBase, Session

from src.common.database import Base, engine, get_db


def test_base_is_declarative_base() -> None:
    assert issubclass(Base, DeclarativeBase)


def test_engine_configured() -> None:
    assert engine.url is not None


def test_get_db_yields_session_and_closes(monkeypatch: pytest.MonkeyPatch) -> None:
    mock_session = MagicMock(spec=Session)
    monkeypatch.setattr("src.common.database.SessionLocal", lambda: mock_session)

    gen = get_db()
    session = next(gen)
    assert session is mock_session

    with pytest.raises(StopIteration):
        next(gen)

    mock_session.close.assert_called_once()
