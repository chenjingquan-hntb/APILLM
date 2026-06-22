"""Tests for router service — upstream ranking and selection."""
import pytest
from unittest.mock import patch, AsyncMock
from app.db.models import Upstream, UpstreamProtocol
from app.core.exceptions import NoAvailableUpstreamError


def make_upstream(id: int, name: str, priority: int = 0, base_url: str = "https://api.test.com"):
    return Upstream(
        id=id, name=name, base_url=base_url, api_key="sk-test",
        protocol=UpstreamProtocol.openai, priority=priority, is_enabled=True,
    )


class TestSelectUpstream:
    def test_select_first_available(self):
        from app.services.router import select_upstream
        upstreams = [make_upstream(1, "a"), make_upstream(2, "b")]
        result = select_upstream(upstreams)
        assert result.id == 1

    def test_empty_upstreams_raises(self):
        from app.services.router import select_upstream
        with pytest.raises(NoAvailableUpstreamError):
            select_upstream([])

    def test_single_upstream(self):
        from app.services.router import select_upstream
        u = make_upstream(1, "only")
        assert select_upstream([u]).id == 1


@pytest.mark.asyncio
async def test_rank_by_manual_price():
    """Manual-priced models should use priority ordering (not Redis price)."""
    from app.services.router import rank_upstreams_by_model

    cheap = make_upstream(1, "cheap", priority=10)
    expensive = make_upstream(2, "expensive", priority=50)

    manual_prices = {"test-model": {"prompt": 0.001, "completion": 0.003}}
    ranked = await rank_upstreams_by_model(
        [cheap, expensive], "test-model", manual_prices=manual_prices
    )
    # Should be sorted by priority desc when manual price applies
    assert ranked[0].id == 2  # higher priority first
    assert ranked[1].id == 1


@pytest.mark.asyncio
async def test_rank_by_redis_price():
    """When prices available in Redis, sort by cheapest (prompt + completion)."""
    from app.services.router import rank_upstreams_by_model

    cheap = make_upstream(1, "cheap")
    expensive = make_upstream(2, "expensive")

    with patch("app.services.router.cache_mget") as mock_mget:
        mock_mget.return_value = [
            {"prompt": 0.001, "completion": 0.003},
            {"prompt": 0.050, "completion": 0.150},
        ]
        ranked = await rank_upstreams_by_model([cheap, expensive], "gpt-4o")

    assert ranked[0].id == 1  # cheapest first
    assert ranked[1].id == 2


@pytest.mark.asyncio
async def test_rank_with_some_unpriced():
    """Unpriced upstreams should go to the end of the list."""
    from app.services.router import rank_upstreams_by_model

    cheap = make_upstream(1, "cheap")
    unpriced = make_upstream(2, "unpriced")

    with patch("app.services.router.cache_mget") as mock_mget:
        mock_mget.return_value = [
            {"prompt": 0.001, "completion": 0.003},
            None,
        ]
        ranked = await rank_upstreams_by_model([cheap, unpriced], "gpt-4o")

    assert ranked[0].id == 1
    assert ranked[1].id == 2


@pytest.mark.asyncio
async def test_rank_fallback_priority():
    """When no price data at all, use priority-based sorting."""
    from app.services.router import rank_upstreams_by_model

    low_prio = make_upstream(1, "low", priority=10)
    high_prio = make_upstream(2, "high", priority=50)

    with patch("app.services.router.cache_mget") as mock_mget:
        mock_mget.return_value = [None, None]

        # Also simulate Redis unavailable
        ranked = await rank_upstreams_by_model([low_prio, high_prio], "unknown-model")

    assert ranked[0].id == 2  # high priority first
    assert ranked[1].id == 1
