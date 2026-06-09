"""Tests for optimization config loading."""

from __future__ import annotations

from pathlib import Path

from mnemonic.config import OptimizationConfig, load_config


def _write_config(tmp_path: Path, vault_path: Path, extra: str = "") -> Path:
    cfg = tmp_path / "config.toml"
    cfg.write_text(
        f"""
[vault]
path = "{vault_path}"

[llm]
api_key_env = "KEY"
model_default = "m"
model_rephrase = "m"
model_offline = "m"
[llm.budget]
daily_cents = 100
monthly_cents = 1000

[defaults]
variation_enabled = true
variation_frequency = 0.3
leech_threshold = 8
daily_review_limit = 100
daily_new_limit = 20
{extra}
"""
    )
    return cfg


def test_optimization_defaults_when_section_absent(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg_path = _write_config(tmp_path, vault)
    config = load_config(user_global_path=cfg_path)
    assert isinstance(config.optimization, OptimizationConfig)
    assert config.optimization.reward_decay_gamma == 0.5
    assert config.optimization.reward_window_k == 3


def test_optimization_overrides_from_section(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    extra = "[optimization]\nreward_decay_gamma = 0.7\nreward_window_k = 5\n"
    cfg_path = _write_config(tmp_path, vault, extra)
    config = load_config(user_global_path=cfg_path)
    assert config.optimization.reward_decay_gamma == 0.7
    assert config.optimization.reward_window_k == 5
