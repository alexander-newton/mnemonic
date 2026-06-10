"""Tests for the OpenRouter-pinned DSPy LM builder and usage harvest."""

from __future__ import annotations

import pytest

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.dspy_lm import build_openrouter_lm, harvest_usage
from mnemonic.exceptions import LLMConfigError


def test_build_lm_requires_openrouter_key(monkeypatch):
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    cfg = OptimizationConfig()
    with pytest.raises(LLMConfigError, match="OPENROUTER_API_KEY"):
        build_openrouter_lm(model="openrouter/anthropic/claude-3.5-haiku", config=cfg)


def test_build_lm_rejects_non_openrouter_model(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    cfg = OptimizationConfig()
    with pytest.raises(LLMConfigError, match="openrouter/"):
        build_openrouter_lm(model="anthropic/claude-3.5-haiku", config=cfg)


def test_build_lm_configures_openrouter(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "sk-or-test")
    cfg = OptimizationConfig()
    lm = build_openrouter_lm(model="openrouter/anthropic/claude-3.5-haiku", config=cfg)
    assert lm.model == "openrouter/anthropic/claude-3.5-haiku"
    assert lm.kwargs.get("api_base") == "https://openrouter.ai/api/v1"


def test_harvest_usage_prefers_openrouter_usage_cost():
    history = [
        {"usage": {"prompt_tokens": 100, "completion_tokens": 20, "cost": 0.001},
         "cost": 0.0},
        {"usage": {"prompt_tokens": 50, "completion_tokens": 10, "cost": 0.0005},
         "cost": None},
    ]
    totals = harvest_usage(history)
    assert totals.input_tokens == 150
    assert totals.output_tokens == 30
    assert totals.cost_millicents == 150


def test_harvest_usage_falls_back_to_top_level_cost():
    history = [
        {"usage": {"prompt_tokens": 10, "completion_tokens": 5}, "cost": 0.002},
        {"usage": {"prompt_tokens": 0, "completion_tokens": 0}, "cost": None},
    ]
    totals = harvest_usage(history)
    assert totals.input_tokens == 10
    assert totals.output_tokens == 5
    assert totals.cost_millicents == 200
