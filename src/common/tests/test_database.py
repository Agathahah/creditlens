import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.common.database import DatabaseManager

@pytest.mark.asyncio
async def test_database_manager_diagnostics():
    # Setup mock manager with mocked engines and clients to run diagnostic tests offline
    with patch("src.common.database.create_async_engine"), \
         patch("redis.asyncio.from_url") as mock_redis_factory:
        
        manager = DatabaseManager()
        
        # Mock connection success behaviors
        mock_session = AsyncMock()
        manager.async_session_factory = MagicMock(return_value=mock_session)
        
        mock_redis = AsyncMock()
        mock_redis.ping.return_value = True
        mock_redis_factory.return_value = mock_redis
        
        diagnostics = await manager.health_check()
        assert diagnostics["postgres"] == "healthy"
        assert diagnostics["redis"] == "healthy"
