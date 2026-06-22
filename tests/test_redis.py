"""Tests for redis service — graceful degradation and connection management."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class TestRedisInit:
    @pytest.mark.asyncio
    async def test_init_success(self):
        with patch("app.services.redis.aioredis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.Redis.return_value = mock_client
            mock_redis.ConnectionPool.from_url.return_value = MagicMock()
            mock_client.ping.return_value = True

            from app.services.redis import init_redis
            result = await init_redis()
            assert result is True

    @pytest.mark.asyncio
    async def test_init_failure_graceful(self):
        with patch("app.services.redis.aioredis") as mock_redis:
            mock_redis.ConnectionPool.from_url.side_effect = Exception("Connection refused")

            from app.services.redis import init_redis
            result = await init_redis()
            assert result is False

    @pytest.mark.asyncio
    async def test_init_ping_failure(self):
        with patch("app.services.redis.aioredis") as mock_redis:
            mock_client = AsyncMock()
            mock_redis.Redis.return_value = mock_client
            mock_redis.ConnectionPool.from_url.return_value = MagicMock()
            mock_client.ping.side_effect = Exception("Ping failed")

            from app.services.redis import init_redis
            result = await init_redis()
            assert result is False


class TestRedisClose:
    @pytest.mark.asyncio
    async def test_close_cleanup(self):
        with patch("app.services.redis.aioredis") as mock_redis:
            mock_client = AsyncMock()
            mock_pool = MagicMock()

            # Set globals
            import app.services.redis as redis_mod
            redis_mod._client = mock_client
            redis_mod._pool = mock_pool

            await redis_mod.close_redis()

            mock_client.aclose.assert_awaited_once()
            mock_pool.disconnect.assert_called_once()
            assert redis_mod._client is None
            assert redis_mod._pool is None

    @pytest.mark.asyncio
    async def test_close_noop_when_none(self):
        import app.services.redis as redis_mod
        redis_mod._client = None
        redis_mod._pool = None

        # Should not raise
        await redis_mod.close_redis()


class TestGetRedis:
    @pytest.mark.asyncio
    async def test_cooldown_prevents_storm(self):
        import app.services.redis as redis_mod
        redis_mod._client = None
        redis_mod._last_reconnect_attempt = 100.0  # Far in the past

        # Mock init to fail
        with patch.object(redis_mod, "init_redis", AsyncMock(return_value=False)):
            # First call should attempt reconnect (cooldown cleared)
            with pytest.raises(RuntimeError, match="not initialized"):
                await redis_mod.get_redis()

            # Set last attempt to "now" so cooldown is active
            import time
            redis_mod._last_reconnect_attempt = time.monotonic()

            # Second call should hit cooldown
            with pytest.raises(RuntimeError, match="cooldown"):
                await redis_mod.get_redis()


class TestCacheFunctions:
    @pytest.mark.asyncio
    async def test_cache_get_success(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client
            mock_client.get.return_value = '{"key": "value"}'

            from app.services.redis import cache_get
            result = await cache_get("test-key")
            assert result == {"key": "value"}

    @pytest.mark.asyncio
    async def test_cache_get_none(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client
            mock_client.get.return_value = None

            from app.services.redis import cache_get
            result = await cache_get("missing-key")
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_get_graceful_failure(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_get_redis.side_effect = RuntimeError("Redis down")

            from app.services.redis import cache_get
            result = await cache_get("any-key")
            assert result is None

    @pytest.mark.asyncio
    async def test_cache_set_success(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client

            from app.services.redis import cache_set
            await cache_set("key", {"val": 1}, ttl=300)

            mock_client.setex.assert_called_once()

    @pytest.mark.asyncio
    async def test_cache_set_graceful_failure(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_get_redis.side_effect = RuntimeError("Redis down")

            from app.services.redis import cache_set
            # Should not raise
            await cache_set("key", {"val": 1})

    @pytest.mark.asyncio
    async def test_cache_mget_success(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client
            mock_client.mget.return_value = ['{"a": 1}', None, '{"b": 2}']

            from app.services.redis import cache_mget
            results = await cache_mget(["k1", "k2", "k3"])
            assert results == [{"a": 1}, None, {"b": 2}]

    @pytest.mark.asyncio
    async def test_cache_mget_empty(self):
        from app.services.redis import cache_mget
        results = await cache_mget([])
        assert results == []

    @pytest.mark.asyncio
    async def test_cache_mget_graceful_failure(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_get_redis.side_effect = RuntimeError("Redis down")

            from app.services.redis import cache_mget
            results = await cache_mget(["k1"])
            assert results == []

    @pytest.mark.asyncio
    async def test_cache_delete_success(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client
            mock_client.delete.return_value = 2

            from app.services.redis import cache_delete
            count = await cache_delete("k1", "k2")
            assert count == 2

    @pytest.mark.asyncio
    async def test_cache_delete_empty(self):
        from app.services.redis import cache_delete
        count = await cache_delete()
        assert count == 0

    @pytest.mark.asyncio
    async def test_cache_exists(self):
        with patch("app.services.redis.get_redis") as mock_get_redis:
            mock_client = AsyncMock()
            mock_get_redis.return_value = mock_client
            mock_client.exists.return_value = 1

            from app.services.redis import cache_exists
            count = await cache_exists("key")
            assert count == 1
