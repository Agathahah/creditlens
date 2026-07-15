"""SQLAlchemy engine, session factory, and declarative base for CreditLens."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from src.common.config import get_settings


class Base(DeclarativeBase):
    """Base class for all CreditLens ORM models."""


engine = create_engine(get_settings().postgres_url, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Yield a database session for request-scoped usage."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
