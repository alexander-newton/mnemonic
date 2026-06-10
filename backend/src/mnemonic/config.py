"""Configuration loader for Mnemonic.

Loads from ~/.config/mnemonic/config.toml (user-global) overlaid by
<vault>/.mnemonic/config.toml (vault-local). Vault-local wins per-key.
"""

from __future__ import annotations

import tomllib
from dataclasses import dataclass, field
from pathlib import Path

from mnemonic.exceptions import VaultNotConfiguredError


@dataclass(frozen=True)
class VaultConfig:
    path: Path
    remote: str | None
    branch: str
    watch: bool


@dataclass(frozen=True)
class BudgetConfig:
    daily_cents: int
    monthly_cents: int


@dataclass(frozen=True)
class LLMConfig:
    api_key_env: str
    model_default: str
    model_rephrase: str
    model_offline: str
    budget: BudgetConfig
    api_base: str = "https://openrouter.ai/api"


@dataclass(frozen=True)
class DefaultsConfig:
    variation_enabled: bool
    variation_frequency: float
    leech_threshold: int
    daily_review_limit: int
    daily_new_limit: int


@dataclass(frozen=True)
class OptimizationConfig:
    reward_decay_gamma: float = 0.5
    reward_window_k: int = 3
    min_interval_hours: float = 20.0
    demo_margin_delta: float = 0.1


@dataclass(frozen=True)
class Config:
    vault: VaultConfig
    llm: LLMConfig
    defaults: DefaultsConfig
    optimization: OptimizationConfig = field(default_factory=OptimizationConfig)


def _deep_merge(base: dict, overlay: dict) -> dict:
    out = dict(base)
    for key, value in overlay.items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _deep_merge(out[key], value)
        else:
            out[key] = value
    return out


def _user_global_default() -> Path:
    return Path.home() / ".config" / "mnemonic" / "config.toml"


def load_config(*, user_global_path: Path | None = None) -> Config:
    """Load merged config. Returns frozen Config dataclass.

    Raises:
        VaultNotConfiguredError: if vault.path is missing or empty after merge.
    """
    user_path = user_global_path or _user_global_default()
    if not user_path.exists():
        raise VaultNotConfiguredError(
            f"User config missing at {user_path}. "
            "Run `mnemonic init` or create the file manually with [vault], [llm], [defaults] sections."
        )
    user_data = tomllib.loads(user_path.read_text())

    vault_path_str = user_data.get("vault", {}).get("path", "")
    if not vault_path_str:
        raise VaultNotConfiguredError(
            "[vault] path is missing in config. " f"Set vault.path in {user_path}."
        )
    vault_path = Path(vault_path_str)

    vault_local_path = vault_path / ".mnemonic" / "config.toml"
    if vault_local_path.exists():
        vault_data = tomllib.loads(vault_local_path.read_text())
        merged = _deep_merge(user_data, vault_data)
    else:
        merged = user_data

    vault_section = merged["vault"]
    llm_section = merged["llm"]
    budget_section = llm_section["budget"]
    defaults_section = merged["defaults"]
    opt_section = merged.get("optimization", {})
    optimization = OptimizationConfig(
        reward_decay_gamma=opt_section.get("reward_decay_gamma", 0.5),
        reward_window_k=opt_section.get("reward_window_k", 3),
        min_interval_hours=opt_section.get("min_interval_hours", 20.0),
        demo_margin_delta=opt_section.get("demo_margin_delta", 0.1),
    )

    return Config(
        vault=VaultConfig(
            path=Path(vault_section["path"]),
            remote=vault_section.get("remote"),
            branch=vault_section.get("branch", "main"),
            watch=vault_section.get("watch", False),
        ),
        llm=LLMConfig(
            api_key_env=llm_section["api_key_env"],
            model_default=llm_section["model_default"],
            model_rephrase=llm_section["model_rephrase"],
            model_offline=llm_section["model_offline"],
            budget=BudgetConfig(
                daily_cents=budget_section["daily_cents"],
                monthly_cents=budget_section["monthly_cents"],
            ),
            api_base=llm_section.get("api_base", "https://openrouter.ai/api"),
        ),
        defaults=DefaultsConfig(
            variation_enabled=defaults_section["variation_enabled"],
            variation_frequency=defaults_section["variation_frequency"],
            leech_threshold=defaults_section["leech_threshold"],
            daily_review_limit=defaults_section["daily_review_limit"],
            daily_new_limit=defaults_section["daily_new_limit"],
        ),
        optimization=optimization,
    )
