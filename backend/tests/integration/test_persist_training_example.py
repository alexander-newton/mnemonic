"""Tests for unlabeled TrainingExample creation and its new columns."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.db.models import Base, TrainingExample


def _memory_engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_training_example_supports_unlabeled_state():
    engine = _memory_engine()
    with Session(engine) as s:
        s.add(
            TrainingExample(
                id="te1",
                card_id="c1",
                variation_id="v1",
                prompt_version_id="pv1",
                base_q="base front",
                base_a="base back",
                variation_q="vary front",
                variation_a="vary back",
                label=0,
                reward=None,
                maturity=0,
                finalized=False,
                rating=None,
                note_context=None,
                created_at=datetime(2026, 6, 9, 12, 0, 0),
            )
        )
        s.commit()
        row = s.get(TrainingExample, "te1")
        assert row.prompt_version_id == "pv1"
        assert row.reward is None
        assert row.maturity == 0
        assert row.finalized is False
