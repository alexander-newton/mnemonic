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
