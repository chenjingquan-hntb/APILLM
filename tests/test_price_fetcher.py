"""Tests for price_fetcher — _nested_get and _fetch_one."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.price_fetcher import _nested_get


# ============================================================
# _nested_get (pure logic)
# ============================================================
class TestNestedGet:
    def test_simple_key(self):
        assert _nested_get({"a": 1}, "a") == 1

    def test_nested_path(self):
        data = {"pricing": {"prompt": 0.005, "completion": 0.015}}
        assert _nested_get(data, "pricing.prompt") == 0.005
        assert _nested_get(data, "pricing.completion") == 0.015

    def test_missing_key(self):
        assert _nested_get({"a": 1}, "b") is None

    def test_missing_nested_key(self):
        assert _nested_get({"a": {"b": 1}}, "a.c") is None

    def test_path_too_deep(self):
        assert _nested_get({"a": 1}, "a.b.c") is None

    def test_empty_dict(self):
        assert _nested_get({}, "anything") is None

    def test_float_value(self):
        assert _nested_get({"price": 0.005}, "price") == 0.005

    def test_string_value(self):
        assert _nested_get({"id": "gpt-4o"}, "id") == "gpt-4o"


# ============================================================
# _fetch_one — unit tests with mocked HTTP
# ============================================================
@pytest.fixture
def mock_upstream():
    from app.db.models import Upstream, UpstreamProtocol
    u = Upstream(
        id=1,
        name="test-upstream",
        base_url="https://api.test.com",
        api_key="sk-test",
        protocol=UpstreamProtocol.openai,
        priority=10,
        is_enabled=True,
        pricing_config={
            "model_id_field": "id",
            "prompt_price_field": "pricing.prompt",
            "completion_price_field": "pricing.completion",
        },
    )
    return u


@pytest.mark.asyncio
async def test_fetch_one_success(mock_upstream):
    from app.services.price_fetcher import _fetch_one

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "pricing": {"prompt": 0.005, "completion": 0.015}},
            {"id": "gpt-4o-mini", "pricing": {"prompt": 0.00015, "completion": 0.0006}},
        ],
    }

    with patch("app.services.price_fetcher._price_client") as mock_client:
        mock_client.get.return_value = mock_response
        results = await _fetch_one(mock_upstream)

    assert len(results) == 2
    assert results[0]["model"] == "gpt-4o"
    assert results[0]["prompt"] == 0.005
    assert results[0]["completion"] == 0.015
    assert results[1]["model"] == "gpt-4o-mini"
    assert results[1]["prompt"] == 0.00015


@pytest.mark.asyncio
async def test_fetch_one_no_pricing_config(mock_upstream):
    from app.services.price_fetcher import _fetch_one
    mock_upstream.pricing_config = None
    results = await _fetch_one(mock_upstream)
    assert results == []


@pytest.mark.asyncio
async def test_fetch_one_http_error(mock_upstream):
    from app.services.price_fetcher import _fetch_one
    import httpx

    with patch("app.services.price_fetcher._price_client") as mock_client:
        mock_client.get.side_effect = httpx.HTTPError("Connection refused")
        results = await _fetch_one(mock_upstream)

    assert results == []


@pytest.mark.asyncio
async def test_fetch_one_zero_prices(mock_upstream):
    from app.services.price_fetcher import _fetch_one

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "object": "list",
        "data": [
            {"id": "free-model", "pricing": {"prompt": 0, "completion": 0}},
        ],
    }

    with patch("app.services.price_fetcher._price_client") as mock_client:
        mock_client.get.return_value = mock_response
        results = await _fetch_one(mock_upstream)

    assert len(results) == 1
    assert results[0]["prompt"] == 0.0
    assert results[0]["completion"] == 0.0


@pytest.mark.asyncio
async def test_fetch_one_custom_field_config(mock_upstream):
    from app.services.price_fetcher import _fetch_one

    mock_upstream.pricing_config = {
        "model_id_field": "model_name",
        "prompt_price_field": "cost.input",
        "completion_price_field": "cost.output",
    }

    mock_response = AsyncMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "object": "list",
        "data": [
            {"model_name": "custom-model", "cost": {"input": 0.001, "output": 0.002}},
        ],
    }

    with patch("app.services.price_fetcher._price_client") as mock_client:
        mock_client.get.return_value = mock_response
        results = await _fetch_one(mock_upstream)

    assert len(results) == 1
    assert results[0]["model"] == "custom-model"
    assert results[0]["prompt"] == 0.001
    assert results[0]["completion"] == 0.002
