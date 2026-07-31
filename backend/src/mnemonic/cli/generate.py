"""`mnemonic-generate`: generate LLM variations for cards that have none."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from mnemonic.config import load_config
from mnemonic.core.optimization.registry import ensure_champion_versions
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.llm.backends.openrouter import OpenRouterBackend
from mnemonic.llm.variation.generator import VariationGenerator
from mnemonic.services.variation_gen import GenerationReport, run_generate
from mnemonic.vault.repository import VaultRepository

_DEFAULT_LIMIT = 20


def _default_prompts_dir() -> Path:
    from mnemonic.llm.prompts import variation as variation_pkg

    return Path(variation_pkg.__file__).parent


def _format_summary(report: GenerationReport, *, dry_run: bool) -> str:
    """Render a one-glance summary of a generation run."""
    if dry_run:
        listed = "\n".join(f"  {cid}" for cid in report.targets)
        return f"dry run: {len(report.targets)} target(s)\n{listed}".rstrip()
    lines = [
        f"generated {len(report.generated)}, skipped {len(report.skipped)}, "
        f"budget stopped: {'yes' if report.budget_stopped else 'no'}"
    ]
    if report.skipped:
        lines.append("")
        lines.append("skipped:")
        lines.extend(f"  {cid}  {reason}" for cid, reason in report.skipped)
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-generate",
        description="Generate LLM variations for cards that have none.",
    )
    parser.add_argument("--deck", default=None, help="Limit to one deck folder name.")
    parser.add_argument(
        "--limit", type=int, default=_DEFAULT_LIMIT, help="Maximum cards to generate for."
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="List targets without calling the LLM."
    )
    args = parser.parse_args(argv)

    config = load_config()
    engine = create_engine(config.vault.path / ".mnemonic" / "state.sqlite")
    prompts_dir = _default_prompts_dir()
    with session_scope(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=datetime.now())

    generator = (
        None
        if args.dry_run
        else VariationGenerator(
            client=OpenRouterBackend(
                api_key_env=config.llm.api_key_env, base_url=config.llm.api_base
            ),
            prompts_dir=prompts_dir,
        )
    )
    report = run_generate(
        repo=VaultRepository(vault_root=config.vault.path, engine=engine),
        engine=engine,
        generator=generator,
        deck=args.deck,
        limit=args.limit,
        model_default=config.llm.model_default,
        model_rephrase=config.llm.model_rephrase,
        daily_cents=config.llm.budget.daily_cents,
        monthly_cents=config.llm.budget.monthly_cents,
        dry_run=args.dry_run,
    )
    print(_format_summary(report, dry_run=args.dry_run))
    return 1 if (report.skipped or report.budget_stopped) else 0
