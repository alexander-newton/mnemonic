"""`mnemonic-optimize <strategy>`: compile a challenger prompt via DSPy/OpenRouter."""

from __future__ import annotations

import argparse
from datetime import datetime

import dspy
from sqlalchemy import Engine

from mnemonic.config import Config, OptimizationConfig, load_config
from mnemonic.core.optimization.compile import compile_challenger
from mnemonic.core.optimization.dspy_lm import build_openrouter_lm
from mnemonic.core.optimization.registry import DEFAULT_STRATEGIES
from mnemonic.db.models import PromptVersion
from mnemonic.db.sqlite import create_engine
from mnemonic.llm.budget import BudgetGuard


def run_optimize(
    *,
    engine: Engine,
    strategy: str,
    config: OptimizationConfig,
    lm: dspy.BaseLM,
    now: datetime,
) -> PromptVersion:
    """Compile a challenger with an injected LM (testable seam).

    Args:
        engine: SQLAlchemy engine for the state DB.
        strategy: Strategy to optimize.
        config: Optimization config.
        lm: A configured DSPy LM.
        now: Timestamp for the new rows.

    Returns:
        The new challenger PromptVersion.
    """
    return compile_challenger(engine, strategy=strategy, config=config, lm=lm, now=now)


def _resolve(config: Config, engine: Engine) -> tuple[OptimizationConfig, dspy.BaseLM]:
    """Budget pre-check and OpenRouter LM construction from full config."""
    BudgetGuard(
        engine=engine,
        daily_cents=config.llm.budget.daily_cents,
        monthly_cents=config.llm.budget.monthly_cents,
    ).assert_within_budget()
    lm = build_openrouter_lm(model=config.llm.model_offline, config=config.optimization)
    return config.optimization, lm


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-optimize",
        description="Compile a challenger variation prompt for a strategy.",
    )
    parser.add_argument("strategy", choices=DEFAULT_STRATEGIES)
    args = parser.parse_args(argv)

    config = load_config()
    engine = create_engine(config.vault.path / ".mnemonic" / "state.sqlite")
    opt_config, lm = _resolve(config, engine)
    challenger = run_optimize(
        engine=engine,
        strategy=args.strategy,
        config=opt_config,
        lm=lm,
        now=datetime.now(),
    )
    print(
        f"compiled challenger {challenger.strategy} v{challenger.version_no} "
        f"({challenger.id}) from {challenger.compiled_from_n_examples} examples"
    )
    return 0
