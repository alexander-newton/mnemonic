from pathlib import Path
import pytest
from mnemonic.config import Config, load_config
from mnemonic.exceptions import VaultNotConfiguredError


def test_load_user_global_only(tmp_path: Path):
    user_cfg = tmp_path / "config.toml"
    user_cfg.write_text(
        '[vault]\npath = "/tmp/v"\nremote = "git@x.com:u/v.git"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "ANTHROPIC_API_KEY"\nmodel_default = "claude-sonnet-4-6"\n'
        'model_rephrase = "claude-haiku-4-5"\nmodel_offline = "claude-opus-4-7"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    cfg = load_config(user_global_path=user_cfg)
    assert cfg.vault.path == Path("/tmp/v")
    assert cfg.vault.branch == "main"
    assert cfg.llm.model_default == "claude-sonnet-4-6"
    assert cfg.llm.budget.daily_cents == 25
    assert cfg.defaults.variation_frequency == 0.5


def test_vault_local_overrides_user_global(tmp_path: Path):
    user_cfg = tmp_path / "user.toml"
    user_cfg.write_text(
        '[vault]\npath = "' + str(tmp_path) + '"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "ANTHROPIC_API_KEY"\nmodel_default = "claude-sonnet-4-6"\n'
        'model_rephrase = "claude-haiku-4-5"\nmodel_offline = "claude-opus-4-7"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    vault_local_dir = tmp_path / ".mnemonic"
    vault_local_dir.mkdir()
    (vault_local_dir / "config.toml").write_text(
        '[defaults]\nvariation_frequency = 0.6\n'
    )
    cfg = load_config(user_global_path=user_cfg)
    assert cfg.defaults.variation_frequency == 0.6
    assert cfg.defaults.leech_threshold == 8  # not overridden


def test_missing_vault_path_raises(tmp_path: Path):
    user_cfg = tmp_path / "config.toml"
    user_cfg.write_text(
        '[llm]\napi_key_env = "ANTHROPIC_API_KEY"\nmodel_default = "claude-sonnet-4-6"\n'
        'model_rephrase = "claude-haiku-4-5"\nmodel_offline = "claude-opus-4-7"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    with pytest.raises(VaultNotConfiguredError):
        load_config(user_global_path=user_cfg)


def test_llm_api_base_defaults_to_openrouter(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[vault]\npath = "/tmp/v"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "OPENROUTER_API_KEY"\nmodel_default = "anthropic/claude-sonnet-4"\n'
        'model_rephrase = "anthropic/claude-3.5-haiku"\nmodel_offline = "openrouter/anthropic/claude-3.5-haiku"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    cfg = load_config(user_global_path=cfg_path)
    assert cfg.llm.api_base == "https://openrouter.ai/api"


def test_llm_api_base_override(tmp_path: Path):
    cfg_path = tmp_path / "config.toml"
    cfg_path.write_text(
        '[vault]\npath = "/tmp/v"\nbranch = "main"\nwatch = false\n'
        '[llm]\napi_key_env = "OPENROUTER_API_KEY"\nmodel_default = "anthropic/claude-sonnet-4"\n'
        'model_rephrase = "anthropic/claude-3.5-haiku"\nmodel_offline = "openrouter/anthropic/claude-3.5-haiku"\n'
        'api_base = "https://openrouter.ai/api"\n'
        '[llm.budget]\ndaily_cents = 25\nmonthly_cents = 500\n'
        '[defaults]\nvariation_enabled = true\nvariation_frequency = 0.5\n'
        'leech_threshold = 8\ndaily_review_limit = 50\ndaily_new_limit = 10\n'
    )
    cfg = load_config(user_global_path=cfg_path)
    assert cfg.llm.api_base == "https://openrouter.ai/api"
