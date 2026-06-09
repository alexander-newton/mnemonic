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


def test_persist_variation_writes_unlabeled_training_example(tmp_path):
    from mnemonic.db.models import VariationMeta
    from mnemonic.db.sqlite import create_engine
    from mnemonic.llm.variation.generator import GeneratedVariation
    from mnemonic.llm.variation.writer import persist_variation

    vault = tmp_path / "vault"
    note = vault / "note.md"
    note.parent.mkdir(parents=True)
    note.write_text("# Card\n\nfront\n\n## Answer\n\nback\n")

    engine = create_engine(tmp_path / "state.sqlite")
    Base.metadata.create_all(engine)

    variation = GeneratedVariation(
        strategy="rephrase",
        question="reworded?",
        answer="same answer",
        model="claude",
        cost_millicents=10,
        raw_response="Q: reworded?\nA: same answer",
        input_tokens=5,
        output_tokens=5,
    )

    variation_id = persist_variation(
        engine=engine,
        note_path=note,
        card_id="c1",
        variation=variation,
        vault_root=vault,
        prompt_version_id="pv1",
        arm="champion",
        base_q="front",
        base_a="back",
        note_context="some context",
    )

    with Session(engine) as s:
        te = s.query(TrainingExample).filter_by(variation_id=variation_id).one()
        assert te.prompt_version_id == "pv1"
        assert te.reward is None
        assert te.finalized is False
        assert te.base_q == "front"
        assert te.variation_q == "reworded?"
        vm = s.query(VariationMeta).filter_by(id=variation_id).one()
        assert vm.prompt_version_id == "pv1"
        assert vm.arm == "champion"
