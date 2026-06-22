"""Tests for models layer — manual price resolution logic."""
import pytest
from app.api.v1.models import _resolve_manual_cost
from app.db.models import ModelConfig


def _mc(manual_prompt=None, manual_completion=None):
    return ModelConfig(
        model_id="test-model",
        manual_prompt_price=manual_prompt,
        manual_completion_price=manual_completion,
        is_enabled=True,
    )


class TestResolveManualCost:
    def test_both_prices_set(self):
        configs = {"test-model": _mc(0.003, 0.015)}
        cost = _resolve_manual_cost("test-model", configs)
        assert cost == 0.018

    def test_only_prompt_price(self):
        """Should work with only prompt price (matching _build_manual_prices behavior)."""
        configs = {"test-model": _mc(manual_prompt=0.005)}
        cost = _resolve_manual_cost("test-model", configs)
        assert cost == 0.005

    def test_only_completion_price(self):
        configs = {"test-model": _mc(manual_completion=0.010)}
        cost = _resolve_manual_cost("test-model", configs)
        assert cost == 0.01

    def test_both_none(self):
        configs = {"test-model": _mc()}
        assert _resolve_manual_cost("test-model", configs) is None

    def test_zero_price(self):
        configs = {"test-model": _mc(0.0, 0.0)}
        assert _resolve_manual_cost("test-model", configs) is None

    def test_model_not_in_configs(self):
        assert _resolve_manual_cost("nonexistent", {}) is None

    def test_rounding(self):
        configs = {"test-model": _mc(0.001234, 0.002345)}
        cost = _resolve_manual_cost("test-model", configs)
        assert cost == 0.003579

    def test_multiple_models(self):
        configs = {
            "model-a": _mc(0.001, 0.002),
            "model-b": _mc(0.003, 0.004),
            "model-c": _mc(),
        }
        assert _resolve_manual_cost("model-a", configs) == 0.003
        assert _resolve_manual_cost("model-b", configs) == 0.007
        assert _resolve_manual_cost("model-c", configs) is None
