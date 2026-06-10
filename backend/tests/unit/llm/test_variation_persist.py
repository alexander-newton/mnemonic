"""Tests for persist_variation writing an LLMUsage row."""

from __future__ import annotations

from pathlib import Path

import pytest
from sqlalchemy import select

from mnemonic.db.models import Base, LLMUsage, VariationMeta
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.llm.variation.generator import GeneratedVariation
from mnemonic.llm.variation.writer import persist_variation


@pytest.fixture()
def engine(tmp_path: Path):
    """In-memory SQLite engine with schema created."""
    db_path = tmp_path / "test.sqlite"
    eng = create_engine(db_path)
    Base.metadata.create_all(eng)
    return eng


@pytest.fixture()
def note_path(tmp_path: Path) -> Path:
    """A minimal card-note with a Variations section."""
    vault = tmp_path / "vault"
    vault.mkdir()
    note = vault / "test-note.md"
    note.write_text(
        "---\ntitle: test\n---\n"
        "## Card\n\nA ==term==. ^card-aabbccdd\n\n"
        "## Variations\n\n"
        "<!-- mnemonic:variations:begin -->\n"
        "<!-- mnemonic:variations:end -->\n"
    )
    return note


@pytest.fixture()
def vault_root(tmp_path: Path) -> Path:
    return tmp_path / "vault"


def _make_variation(**kwargs) -> GeneratedVariation:
    defaults = {
        "strategy": "rephrase",
        "question": "What is a term?",
        "answer": "A concept.",
        "model": "claude-haiku-4-5",
        "cost_millicents": 42,
        "raw_response": "Q: What is a term?\nA: A concept.",
        "input_tokens": 100,
        "output_tokens": 20,
        "cache_read_tokens": 10,
        "cache_creation_tokens": 5,
    }
    defaults.update(kwargs)
    return GeneratedVariation(**defaults)


def test_persist_variation_writes_llm_usage_row(engine, note_path, vault_root):
    """persist_variation must insert exactly one LLMUsage row with correct fields."""
    variation = _make_variation()

    persist_variation(
        engine=engine,
        note_path=note_path,
        card_id="card-aabbccdd",
        variation=variation,
        vault_root=vault_root,
        prompt_version_id="pv-test",
        base_q="What is a term?",
        base_a="A concept.",
    )

    with session_scope(engine) as s:
        rows = list(s.execute(select(LLMUsage)).scalars().all())

    assert len(rows) == 1
    row = rows[0]
    assert row.purpose == f"variation:{variation.strategy}"
    assert row.model == variation.model
    assert row.card_id == "card-aabbccdd"
    assert row.cost_millicents == 42
    assert row.input_tokens == 100
    assert row.output_tokens == 20
    assert row.cache_read_tokens == 10
    assert row.cache_creation_tokens == 5


def test_persist_variation_still_writes_variation_meta(engine, note_path, vault_root):
    """persist_variation must also write the VariationMeta row (regression guard)."""
    variation = _make_variation()

    persist_variation(
        engine=engine,
        note_path=note_path,
        card_id="card-aabbccdd",
        variation=variation,
        vault_root=vault_root,
        prompt_version_id="pv-test",
        base_q="What is a term?",
        base_a="A concept.",
    )

    with session_scope(engine) as s:
        rows = list(s.execute(select(VariationMeta)).scalars().all())

    assert len(rows) == 1
    assert rows[0].card_id == "card-aabbccdd"
    assert rows[0].strategy == "rephrase"


def test_persist_variation_purpose_contains_strategy(engine, note_path, vault_root):
    """LLMUsage.purpose must be 'variation:<strategy>' for each strategy."""
    for strategy in ("rephrase", "specialize", "generalize"):
        note = note_path.parent / f"note-{strategy}.md"
        note.write_text(
            "---\ntitle: test\n---\n"
            "## Card\n\nA ==term==. ^card-aabbccdd\n\n"
            "## Variations\n\n"
            "<!-- mnemonic:variations:begin -->\n"
            "<!-- mnemonic:variations:end -->\n"
        )
        variation = _make_variation(strategy=strategy)
        persist_variation(
            engine=engine,
            note_path=note,
            card_id=f"card-{strategy}",
            variation=variation,
            vault_root=vault_root,
            prompt_version_id="pv-test",
            base_q="What is a term?",
            base_a="A concept.",
        )

    with session_scope(engine) as s:
        rows = list(s.execute(select(LLMUsage)).scalars().all())

    purposes = {r.purpose for r in rows}
    assert purposes == {"variation:rephrase", "variation:specialize", "variation:generalize"}
