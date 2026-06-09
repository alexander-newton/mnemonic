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
