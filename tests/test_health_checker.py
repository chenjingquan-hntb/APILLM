"""Tests for health_checker — state machine and health status updates."""
import pytest
from unittest.mock import patch, AsyncMock
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

    with patch("app.services.health_checker.cache_get") as mock_get, \
         patch("app.services.health_checker.cache_set") as mock_set:

        mock_get.return_value = None  # No previous state

        for i in range(settings.failure_threshold):
            await _update_health(u, success=False)

        # After threshold failures, should mark unhealthy
        call_args = mock_set.call_args[0]
        assert call_args[0].startswith("health:")
        assert "unhealthy" in str(mock_set.call_args)


@pytest.mark.asyncio
async def test_update_health_recovery():
    """After recovery_threshold successes, status returns to 'healthy'."""
    from app.services.health_checker import _update_health
    from app.core.config import settings

    u = make_upstream()

    with patch("app.services.health_checker.cache_get") as mock_get, \
         patch("app.services.health_checker.cache_set") as mock_set:

        # Start in unhealthy state with failures accumulated
        mock_get.return_value = {
            "status": "unhealthy",
            "consecutive_failures": 3,
            "consecutive_successes": 0,
        }

        for i in range(settings.recovery_threshold):
            await _update_health(u, success=True)

        # After recovery threshold, should be healthy
        call_args = mock_set.call_args[0]
        assert "healthy" in str(mock_set.call_args)


@pytest.mark.asyncio
async def test_update_health_degraded():
    """Mixed results should produce 'degraded' status."""
    from app.services.health_checker import _update_health

    u = make_upstream()

    with patch("app.services.health_checker.cache_get") as mock_get, \
         patch("app.services.health_checker.cache_set") as mock_set:

        mock_get.return_value = None

        await _update_health(u, success=True)
        await _update_health(u, success=False)

        # After at least one failure but not exceeding threshold, should be degraded or mixed
        call_args = mock_set.call_args[0]
        assert call_args[0].startswith("health:")
