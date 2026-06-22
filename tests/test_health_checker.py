"""Tests for health_checker — state machine and health status updates."""
import pytest
from unittest.mock import patch
from app.db.models import Upstream, UpstreamProtocol


def make_upstream(id=1, name="test-upstream"):
    return Upstream(
        id=id, name=name, base_url="https://api.test.com",
        api_key="sk-test", protocol=UpstreamProtocol.openai,
        is_enabled=True,
    )


@pytest.mark.asyncio
async def test_update_health_consecutive_failures():
    """After failure_threshold consecutive failures, status becomes 'unhealthy'."""
    from app.services.health_checker import _update_health
    from app.core.config import settings

    u = make_upstream()
    stored: dict = {}

    async def mock_get(key):
        return stored.get(key)

    async def mock_set(key, value, **kwargs):
        stored[key] = value

    with patch("app.services.health_checker.cache_get", side_effect=mock_get), \
         patch("app.services.health_checker.cache_set", side_effect=mock_set):

        for _ in range(settings.failure_threshold):
            await _update_health(u, ok=False)

        state = stored.get(f"health:{u.id}", {})
        assert state.get("status") == "unhealthy"


@pytest.mark.asyncio
async def test_update_health_recovery():
    """After recovery_threshold successes, status returns to 'healthy'."""
    from app.services.health_checker import _update_health
    from app.core.config import settings

    u = make_upstream()
    stored: dict = {
        f"health:{u.id}": {
            "status": "unhealthy",
            "consecutive_failures": 3,
            "consecutive_successes": 0,
            "last_check": 0,
        }
    }

    async def mock_get(key):
        return stored.get(key)

    async def mock_set(key, value, **kwargs):
        stored[key] = value

    with patch("app.services.health_checker.cache_get", side_effect=mock_get), \
         patch("app.services.health_checker.cache_set", side_effect=mock_set):

        for _ in range(settings.recovery_threshold):
            await _update_health(u, ok=True)

        assert stored[f"health:{u.id}"]["status"] == "healthy"


@pytest.mark.asyncio
async def test_update_health_degraded():
    """Mixed results should produce appropriate status."""
    from app.services.health_checker import _update_health

    u = make_upstream()
    stored: dict = {}

    async def mock_get(key):
        return stored.get(key)

    async def mock_set(key, value, **kwargs):
        stored[key] = value

    with patch("app.services.health_checker.cache_get", side_effect=mock_get), \
         patch("app.services.health_checker.cache_set", side_effect=mock_set):

        await _update_health(u, ok=True)
        await _update_health(u, ok=False)

        state = stored.get(f"health:{u.id}", {})
        assert "status" in state
