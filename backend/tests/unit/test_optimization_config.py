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


def test_optimization_phase2_defaults(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    cfg_path = _write_config(tmp_path, vault)
    config = load_config(user_global_path=cfg_path)
    o = config.optimization
    assert o.min_examples_to_compile == 20
    assert o.optimizer == "bootstrap"
    assert o.max_bootstrapped_demos == 4
    assert o.max_labeled_demos == 8
    assert o.val_fraction == 0.3
    assert o.split_seed == 0
    assert o.validity_min_pass_rate == 0.8
    assert o.openrouter_key_env == "OPENROUTER_API_KEY"
    assert o.openrouter_api_base == "https://openrouter.ai/api/v1"


def test_optimization_phase2_overrides(tmp_path):
    vault = tmp_path / "vault"
    vault.mkdir()
    extra = (
        "[optimization]\n"
        "min_examples_to_compile = 5\n"
        'optimizer = "bootstrap"\n'
        "max_bootstrapped_demos = 2\n"
        'openrouter_key_env = "OR_KEY"\n'
    )
    cfg_path = _write_config(tmp_path, vault, extra)
    o = load_config(user_global_path=cfg_path).optimization
    assert o.min_examples_to_compile == 5
    assert o.max_bootstrapped_demos == 2
    assert o.openrouter_key_env == "OR_KEY"
