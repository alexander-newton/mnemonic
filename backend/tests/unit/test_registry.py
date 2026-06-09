"""Tests for the prompt-version registry model and seeding."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.db.models import Base, PromptVersion


def _memory_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_prompt_version_persists_with_defaults():
    engine = _memory_engine()
    with Session(engine) as s:
        s.add(
            PromptVersion(
                id="pv1",
                strategy="rephrase",
                version_no=0,
                instruction_text="seed text",
                demos="[]",
                status="champion",
                parent_version_id=None,
                compiled_from_n_examples=None,
                created_at=datetime(2026, 6, 9, 12, 0, 0),
            )
        )
        s.commit()
        row = s.get(PromptVersion, "pv1")
        assert row.strategy == "rephrase"
        assert row.version_no == 0
        assert row.status == "champion"
        assert row.demos == "[]"


def test_variation_meta_has_prompt_version_and_arm():
    from mnemonic.db.models import VariationMeta

    engine = _memory_engine()
    with Session(engine) as s:
        s.add(
            VariationMeta(
                id="vm1",
                card_id="c1",
                strategy="rephrase",
                model="claude",
                generated_at=datetime(2026, 6, 9, 12, 0, 0),
                shown_count=1,
                helpful_count=0,
                content_hash="abc",
                note_path="note.md",
                prompt_version_id="pv1",
                arm="champion",
            )
        )
        s.commit()
        row = s.get(VariationMeta, "vm1")
        assert row.prompt_version_id == "pv1"
        assert row.arm == "champion"


def test_ensure_champion_versions_seeds_each_strategy(tmp_path):
    from mnemonic.core.optimization.registry import ensure_champion_versions

    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "strategies").mkdir(parents=True)
    for strat in ("rephrase", "specialize", "generalize"):
        (prompts_dir / "strategies" / f"{strat}.md").write_text(f"{strat} instructions")

    engine = _memory_engine()
    with Session(engine) as s:
        created = ensure_champion_versions(
            s, prompts_dir=prompts_dir, now=datetime(2026, 6, 9, 12, 0, 0)
        )
        s.commit()
        assert {pv.strategy for pv in created} == {"rephrase", "specialize", "generalize"}
        champ = s.query(PromptVersion).filter_by(strategy="rephrase").one()
        assert champ.version_no == 0
        assert champ.status == "champion"
        assert champ.instruction_text == "rephrase instructions"


def test_ensure_champion_versions_is_idempotent(tmp_path):
    from mnemonic.core.optimization.registry import ensure_champion_versions

    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "strategies").mkdir(parents=True)
    for strat in ("rephrase", "specialize", "generalize"):
        (prompts_dir / "strategies" / f"{strat}.md").write_text(f"{strat} v0")

    engine = _memory_engine()
    with Session(engine) as s:
        ensure_champion_versions(s, prompts_dir=prompts_dir, now=datetime(2026, 6, 9))
        s.commit()
        second = ensure_champion_versions(
            s, prompts_dir=prompts_dir, now=datetime(2026, 6, 10)
        )
        s.commit()
        assert second == []
        assert s.query(PromptVersion).count() == 3


def test_get_champion_returns_current_champion(tmp_path):
    from mnemonic.core.optimization.registry import (
        ensure_champion_versions,
        get_champion,
    )

    prompts_dir = tmp_path / "prompts"
    (prompts_dir / "strategies").mkdir(parents=True)
    (prompts_dir / "strategies" / "rephrase.md").write_text("rephrase v0")

    engine = _memory_engine()
    with Session(engine) as s:
        ensure_champion_versions(
            s, prompts_dir=prompts_dir, strategies=("rephrase",), now=datetime(2026, 6, 9)
        )
        s.commit()
        champ = get_champion(s, "rephrase")
        assert champ.strategy == "rephrase"
        assert champ.status == "champion"


def test_get_champion_without_seed_fails_loudly():
    from mnemonic.core.optimization.registry import get_champion
    from mnemonic.exceptions import OptimizationError

    engine = _memory_engine()
    with Session(engine) as s:
        try:
            get_champion(s, "rephrase")
            assert False, "expected OptimizationError"
        except OptimizationError as err:
            assert "rephrase" in str(err)
