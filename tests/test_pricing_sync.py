"""Tests for pricing_sync service."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock


class MockPricingResponse:
    """Simple httpx response mock — json() is sync (matches httpx.Response)."""
    def __init__(self, json_data, status_code=200):
        self.status_code = status_code
        self._json_data = json_data

    def raise_for_status(self):
        pass

    def json(self):
        return self._json_data


@pytest.mark.asyncio
async def test_sync_pricing_to_db_creates_new_models():
    from app.services.pricing_sync import sync_pricing_to_db
    from app.db.models import ModelConfig

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_resp = MockPricingResponse({
        "data": [
            {"model_name": "gpt-4o", "model_ratio": 1.0, "completion_ratio": 1.0},
            {"model_name": "claude-sonnet-4-6", "model_ratio": 0.5, "completion_ratio": 0.5},
        ],
        "group_ratio": {"default": 1.0},
        "price": 1.0,
        "quota_per_unit": 500000,
    })

    with patch("app.services.pricing_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await sync_pricing_to_db(mock_session_factory)

    assert result["created"] == 2
    assert result["updated"] == 0
    assert result["total"] == 2
    assert mock_session.add.call_count == 2


@pytest.mark.asyncio
async def test_sync_pricing_to_db_updates_existing():
    from app.services.pricing_sync import sync_pricing_to_db
    from app.db.models import ModelConfig

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    existing_mc = ModelConfig(model_id="gpt-4o", manual_prompt_price=0.0, manual_completion_price=0.0)
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = [existing_mc]
    mock_session.execute.return_value = mock_result
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_resp = MockPricingResponse({
        "data": [
            {"model_name": "gpt-4o", "model_ratio": 1.0, "completion_ratio": 1.0},
        ],
        "group_ratio": {"default": 1.0},
        "price": 1.0,
        "quota_per_unit": 500000,
    })

    with patch("app.services.pricing_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await sync_pricing_to_db(mock_session_factory)

    assert result["created"] == 0
    assert result["updated"] == 1
    assert existing_mc.manual_prompt_price > 0


@pytest.mark.asyncio
async def test_sync_pricing_to_db_skips_zero_price_models():
    from app.services.pricing_sync import sync_pricing_to_db

    mock_session = AsyncMock()
    mock_session.__aenter__.return_value = mock_session
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result
    mock_session_factory = MagicMock()
    mock_session_factory.return_value = mock_session

    mock_resp = MockPricingResponse({
        "data": [
            {"model_name": "", "model_ratio": 0.0, "completion_ratio": 0.0},
        ],
        "group_ratio": {"default": 1.0},
        "price": 1.0,
        "quota_per_unit": 500000,
    })

    with patch("app.services.pricing_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get = AsyncMock(return_value=mock_resp)

        result = await sync_pricing_to_db(mock_session_factory)

    assert result["total"] == 0


@pytest.mark.asyncio
async def test_sync_pricing_to_db_raises_on_http_error():
    from app.services.pricing_sync import sync_pricing_to_db

    with patch("app.services.pricing_sync.httpx.AsyncClient") as mock_client_cls:
        mock_client = AsyncMock()
        mock_client_cls.return_value.__aenter__.return_value = mock_client
        mock_client.get.side_effect = Exception("HTTP 500")

        mock_session_factory = MagicMock()

        with pytest.raises(Exception, match="HTTP 500"):
            await sync_pricing_to_db(mock_session_factory)
