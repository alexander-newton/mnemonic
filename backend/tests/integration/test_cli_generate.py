"""Integration test for the mnemonic-generate CLI."""

from __future__ import annotations

import types
from pathlib import Path

from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.services.variation_gen import GenerationReport


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    deck = vault / "01_Projects" / "gt"
    deck.mkdir(parents=True)
    (deck / "_deck.md").write_text(
        "---\ndeck_name: GT\nvariation_enabled: true\nvariation_frequency: 1.0\n"
        "leech_threshold: 8\ndaily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )
    (deck / "n0.qmd").write_text(
        "---\ntitle: n0\n---\n## Card\n\nA {{c1::term}}. ^card-n0\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault


def _config(vault: Path):
    return types.SimpleNamespace(
        vault=types.SimpleNamespace(path=vault),
        llm=types.SimpleNamespace(
            api_key_env="OPENROUTER_API_KEY",
            api_base="https://openrouter.ai/api",
            model_default="d",
            model_rephrase="r",
            budget=types.SimpleNamespace(daily_cents=100, monthly_cents=1000),
        ),
    )


def test_main_dry_run_returns_zero(tmp_path, monkeypatch, capsys):
    from mnemonic.cli import generate as gen_cli

    vault = _vault(tmp_path)
    monkeypatch.setattr(gen_cli, "load_config", lambda: _config(vault))

    exit_code = gen_cli.main(["--dry-run"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "dry run: 1 target" in output


def test_main_returns_one_when_cards_were_skipped(tmp_path, monkeypatch, capsys):
    from mnemonic.cli import generate as gen_cli

    vault = _vault(tmp_path)
    monkeypatch.setattr(gen_cli, "load_config", lambda: _config(vault))
    monkeypatch.setattr(
        gen_cli,
        "run_generate",
        lambda **kwargs: GenerationReport(
            generated=[], skipped=[("card-n0", "LLMError: boom")],
            budget_stopped=False, targets=["card-n0"],
        ),
    )

    exit_code = gen_cli.main([])

    assert exit_code == 1
    out = capsys.readouterr().out
    assert "skipped 1" in out
    assert "card-n0" in out
