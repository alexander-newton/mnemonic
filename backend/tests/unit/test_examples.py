"""Tests for the DSPy trainset builder and deterministic split."""

from __future__ import annotations

from datetime import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.examples import build_trainset, split_examples
from mnemonic.db.models import Base, PromptVersion, TrainingExample
from mnemonic.exceptions import InsufficientDataError


def _engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def _champion(s, strategy="rephrase", pv_id="pv-r"):
    s.add(
        PromptVersion(
            id=pv_id,
            strategy=strategy,
            version_no=0,
            instruction_text="seed",
            demos="[]",
            status="champion",
            parent_version_id=None,
            compiled_from_n_examples=None,
            created_at=datetime(2026, 6, 1),
        )
    )


def _example(s, i, pv_id="pv-r", finalized=True, reward=0.5):
    s.add(
        TrainingExample(
            id=f"te{i}",
            card_id=f"c{i}",
            variation_id=f"v{i}",
            prompt_version_id=pv_id,
            base_q=f"bq{i}",
            base_a=f"ba{i}",
            variation_q=f"vq{i}",
            variation_a=f"va{i}",
            label=1,
            reward=reward,
            maturity=3,
            finalized=finalized,
            rating=None,
            note_context=f"ctx{i}",
            created_at=datetime(2026, 6, 1),
        )
    )


def test_build_trainset_filters_by_strategy_and_finalized():
    engine = _engine()
    with Session(engine) as s:
        _champion(s, "rephrase", "pv-r")
        _champion(s, "specialize", "pv-s")
        for i in range(3):
            _example(s, i, "pv-r", finalized=True)
        _example(s, 99, "pv-r", finalized=False)  # excluded: not finalized
        _example(s, 100, "pv-s", finalized=True)  # excluded: other strategy
        s.commit()
        cfg = OptimizationConfig(min_examples_to_compile=1)
        train = build_trainset(s, strategy="rephrase", config=cfg)
        assert len(train) == 3
        ex = train[0]
        assert set(ex.inputs().keys()) == {"base_q", "base_a", "note_context"}
        assert ex.question.startswith("vq")
        assert ex.answer.startswith("va")
        assert isinstance(ex.reward, float)


def test_build_trainset_raises_when_too_few():
    engine = _engine()
    with Session(engine) as s:
        _champion(s, "rephrase", "pv-r")
        _example(s, 0, "pv-r", finalized=True)
        s.commit()
        cfg = OptimizationConfig(min_examples_to_compile=20)
        with pytest.raises(InsufficientDataError) as ei:
            build_trainset(s, strategy="rephrase", config=cfg)
        assert ei.value.have == 1
        assert ei.value.need == 20


def test_split_is_deterministic_for_a_seed():
    items = list(range(10))
    a_train, a_val = split_examples(items, val_fraction=0.3, seed=0)
    b_train, b_val = split_examples(items, val_fraction=0.3, seed=0)
    assert a_train == b_train and a_val == b_val
    assert len(a_val) == 3 and len(a_train) == 7
    c_train, c_val = split_examples(items, val_fraction=0.3, seed=1)
    assert sorted(c_train + c_val) == items


def test_build_trainset_excludes_null_reward():
    engine = _engine()
    with Session(engine) as s:
        _champion(s, "rephrase", "pv-r")
        _example(s, 0, "pv-r", finalized=True, reward=0.5)
        s.add(
            TrainingExample(
                id="tenull",
                card_id="cnull",
                variation_id="vnull",
                prompt_version_id="pv-r",
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=0,
                reward=None,
                maturity=1,
                finalized=True,
                rating=None,
                note_context="ctx",
                created_at=datetime(2026, 6, 1),
            )
        )
        s.commit()
        cfg = OptimizationConfig(min_examples_to_compile=1)
        train = build_trainset(s, strategy="rephrase", config=cfg)
        assert len(train) == 1  # null-reward row excluded
