"""Shared test fixtures and configuration."""
import asyncio
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from app.core.config import settings
from app.db.models import User, ApiKey, ModelConfig


# ============================================================
# Test Settings Override
# ============================================================
@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ============================================================
# Sample data fixtures
# ============================================================
@pytest.fixture
def sample_upstream_dict():
    return {
        "name": "test-upstream",
        "base_url": "https://api.test.com",
        "api_key": "sk-test-key-12345",
        "protocol": "openai",
        "priority": 10,
        "is_enabled": True,
        "pricing_config": {
            "model_id_field": "id",
            "prompt_price_field": "pricing.prompt",
            "completion_price_field": "pricing.completion",
        },
    }


@pytest.fixture
def sample_model_data():
    """Sample /v1/models response data."""
    return {
        "object": "list",
        "data": [
            {"id": "gpt-4o", "object": "model", "created": 1718841600,
             "pricing": {"prompt": 0.005, "completion": 0.015}},
            {"id": "gpt-4o-mini", "object": "model", "created": 1718841600,
             "pricing": {"prompt": 0.00015, "completion": 0.0006}},
            {"id": "claude-3-haiku", "object": "model", "created": 1718841600,
             "pricing": {"prompt": 0.00025, "completion": 0.00125}},
        ],
    }


@pytest.fixture
def sample_model_configs():
    return {
        "gpt-4o": ModelConfig(
            model_id="gpt-4o",
            manual_prompt_price=0.003,
            manual_completion_price=0.010,
            is_enabled=True,
        ),
        "claude-3-haiku": ModelConfig(
            model_id="claude-3-haiku",
            manual_prompt_price=0.0002,
            manual_completion_price=0.0010,
            is_enabled=True,
        ),
    }
