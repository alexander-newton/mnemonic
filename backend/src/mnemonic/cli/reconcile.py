"""`mnemonic-reconcile`: scan the vault and reconcile card-integrity state.

Detects core-content changes (trivial/material/cloze-structural), auto-invalidates
the reversible derived artefacts (variations, training examples), flags material
changes for the FSRS review panel (never resets scheduling), and reports dangling
references and duplicate cards.
"""

from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.config import load_config
from mnemonic.db.sqlite import create_engine
from mnemonic.services.reconciliation import ReconciliationReport, ReconciliationService


def run_reconcile(*, vault_root: Path, engine: Engine) -> ReconciliationReport:
    """Run one reconciliation pass (testable seam).

    Args:
        vault_root: Root directory of the vault to scan.
        engine: SQLAlchemy engine for the state DB.

    Returns:
        The ReconciliationReport produced by the pass.
    """
    return ReconciliationService(vault_root=vault_root, engine=engine).run()


def _format_summary(report: ReconciliationReport) -> str:
    """Render a one-glance human summary of a reconciliation report."""
    counts = ", ".join(f"{kind}={n}" for kind, n in report.counts.items())
    dangling = report.dangling
    return (
        f"counts: {counts}\n"
        f"dangling: {len(dangling.review_logs)} review / "
        f"{len(dangling.variations)} variation / {len(dangling.parents)} parent\n"
        f"duplicate groups: {len(report.duplicates)}"
    )


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = argparse.ArgumentParser(
        prog="mnemonic-reconcile",
        description="Scan the vault and reconcile card-integrity state.",
    )
    parser.parse_args(argv)

    config = load_config()
    engine = create_engine(config.vault.path / ".mnemonic" / "state.sqlite")
    report = run_reconcile(vault_root=config.vault.path, engine=engine)
    print(_format_summary(report))
    return 0
