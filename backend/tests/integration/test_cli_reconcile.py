"""Integration test for the mnemonic-reconcile CLI."""

from __future__ import annotations

import types
from pathlib import Path

from mnemonic.cli.reconcile import main, run_reconcile
from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine


def _vault_with_card(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nWhat is a {{c1::Nash equilibrium}}?\n"
    )
    return vault


def _engine(vault: Path):
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return engine


def test_run_reconcile_returns_report(tmp_path: Path):
    vault = _vault_with_card(tmp_path)
    engine = _engine(vault)

    report = run_reconcile(vault_root=vault, engine=engine)

    assert report.counts["new"] == 1
    assert report.dangling.parents == []
    assert report.duplicates == []


def test_main_prints_summary_and_returns_zero(tmp_path, monkeypatch, capsys):
    vault = _vault_with_card(tmp_path)
    _engine(vault)  # create schema at the path main() will open
    config = types.SimpleNamespace(vault=types.SimpleNamespace(path=vault))
    monkeypatch.setattr("mnemonic.cli.reconcile.load_config", lambda: config)

    exit_code = main([])

    assert exit_code == 0
    out = capsys.readouterr().out
    assert "new" in out  # the per-kind counts are printed
