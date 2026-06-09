"""`mnemonic-label`: seed champions and run the variation labeling job."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

from mnemonic.config import OptimizationConfig, load_config
from mnemonic.core.optimization.labeling import LabelingReport, run_labeling_job
from mnemonic.core.optimization.registry import ensure_champion_versions
from mnemonic.db.sqlite import create_engine, session_scope


def _default_prompts_dir() -> Path:
    from mnemonic.llm.prompts import variation as variation_pkg

    return Path(variation_pkg.__file__).parent


def run_labeling(
    *,
    db_path: Path,
    prompts_dir: Path,
    config: OptimizationConfig,
    now: datetime,
) -> LabelingReport:
    """Seed champions (idempotent) and run the labeling job.

    Args:
        db_path: Path to the SQLite state database.
        prompts_dir: Directory containing ``strategies/<name>.md`` seed files.
        config: Optimization configuration.
        now: Timestamp used when seeding champion versions.

    Returns:
        The LabelingReport from the run.
    """
    engine = create_engine(db_path)
    with session_scope(engine) as session:
        ensure_champion_versions(session, prompts_dir=prompts_dir, now=now)
    return run_labeling_job(engine, config)


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-label",
        description="Compute durability rewards for shown variations.",
    )
    parser.parse_args(argv)

    config = load_config()
    db_path = config.vault.path / ".mnemonic" / "state.sqlite"
    report = run_labeling(
        db_path=db_path,
        prompts_dir=_default_prompts_dir(),
        config=config.optimization,
        now=datetime.now(),
    )
    print(
        f"labeled={report.labeled} pending={report.pending} "
        f"finalized_skipped={report.finalized_skipped}"
    )
    return 0
