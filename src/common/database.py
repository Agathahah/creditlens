import logging
from collections.abc import AsyncGenerator

import redis.asyncio as redis
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from src.common.config import get_settings

logger = logging.getLogger("creditlens.database")


class Base(DeclarativeBase):
    """Declarative Base class for SQLAlchemy ORM models."""

    pass


class DatabaseManager:
    """Manages transactional and state storage connections for CreditLens."""

    def __init__(self) -> None:
        settings = get_settings()

        # Async engine conversion (ensure using asyncpg driver for sqlalchemy)
        pg_url = settings.POSTGRES_URL
        if pg_url.startswith("postgresql://"):
            pg_url = pg_url.replace("postgresql://", "postgresql+asyncpg://", 1)

        self.async_engine = create_async_engine(
            pg_url, pool_pre_ping=True, pool_size=10, max_overflow=20
        )

        self.async_session_factory = async_sessionmaker(
            bind=self.async_engine, expire_on_commit=False, class_=AsyncSession
        )

        # Redis client pool
        self.redis_client: redis.Redis | None = None
        self.redis_url = settings.REDIS_URL

    async def get_redis(self) -> redis.Redis:
        """Get or initialize the async Redis connection."""
        if self.redis_client is None:
            self.redis_client = redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        return self.redis_client

    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Dependency generator for FastAPI context to yield Async DB sessions."""
        async with self.async_session_factory() as session:
            try:
                yield session
                await session.commit()
            except Exception as e:
                await session.rollback()
                logger.error(f"Async DB Session rolled back due to error: {e}")
                raise e
            finally:
                await session.close()

    async def health_check(self) -> dict[str, str]:
        """Perform system-wide diagnostics on PostgreSQL and Redis dependencies."""
        diagnostics = {"postgres": "unhealthy", "redis": "unhealthy"}

        # 1. Test PostgreSQL
        try:
            async with self.async_session_factory() as session:
                from sqlalchemy import text

                await session.execute(text("SELECT 1"))
                diagnostics["postgres"] = "healthy"
        except Exception as e:
            logger.error(f"PostgreSQL diagnostic health check failed: {e}")

        # 2. Test Redis
        try:
            r_client = await self.get_redis()
            await r_client.ping()
            diagnostics["redis"] = "healthy"
        except Exception as e:
            logger.error(f"Redis diagnostic health check failed: {e}")

        return diagnostics

    async def shutdown(self) -> None:
        """Gracefully release and cleanup all initialized database and cache pools."""
        logger.info("Starting graceful shutdown of database connection pools...")
        await self.async_engine.dispose()
        if self.redis_client is not None:
            await self.redis_client.close()
        logger.info("Connection pools cleaned up.")


# Global instance manager
db_manager = DatabaseManager()
