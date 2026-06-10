"""Integration tests for compile_challenger (DummyLM, no network)."""

from __future__ import annotations

import json
from datetime import datetime

import pytest
from dspy.utils.dummies import DummyLM
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.core.optimization.compile import compile_challenger
from mnemonic.db.models import Base, LLMUsage, PromptVersion, TrainingExample
from mnemonic.exceptions import InsufficientDataError, OptimizationError


def _engine():
    engine = create_engine("sqlite:///:memory:", future=True)
    Base.metadata.create_all(engine)
    return engine


def _seed(engine, n=6, strategy="rephrase", pv_id="pv-r"):
    with Session(engine) as s:
        s.add(
            PromptVersion(
                id=pv_id,
                strategy=strategy,
                version_no=0,
                instruction_text="Rephrase the card.",
                demos="[]",
                status="champion",
                parent_version_id=None,
                compiled_from_n_examples=None,
                created_at=datetime(2026, 6, 1),
            )
        )
        for i in range(n):
            s.add(
                TrainingExample(
                    id=f"te{i}",
                    card_id=f"c{i}",
                    variation_id=f"v{i}",
                    prompt_version_id=pv_id,
                    base_q=f"What is X{i}?",
                    base_a=f"X{i} is Y.",
                    variation_q=f"hist q{i}",
                    variation_a=f"hist a{i}",
                    label=1,
                    reward=0.6,
                    maturity=3,
                    finalized=True,
                    rating=None,
                    note_context="ctx",
                    created_at=datetime(2026, 6, 1),
                )
            )
        s.commit()


def _dummy_lm(n=40):
    return DummyLM([{"question": f"gen q{i}", "answer": f"gen a{i}"} for i in range(n)])


def test_compile_writes_challenger_with_provenance_and_usage():
    engine = _engine()
    _seed(engine, n=6)
    cfg = OptimizationConfig(
        min_examples_to_compile=2,
        max_bootstrapped_demos=2,
        val_fraction=0.34,
        validity_min_pass_rate=0.5,
    )
    challenger = compile_challenger(
        engine,
        strategy="rephrase",
        config=cfg,
        lm=_dummy_lm(),
        now=datetime(2026, 6, 9, 12, 0, 0),
    )
    with Session(engine) as s:
        row = s.get(PromptVersion, challenger.id)
        assert row.status == "challenger"
        assert row.strategy == "rephrase"
        assert row.parent_version_id == "pv-r"
        assert row.version_no == 1
        assert row.compiled_from_n_examples is not None
        demos = json.loads(row.demos)
        assert isinstance(demos, list)
        usage = (
            s.execute(select(LLMUsage).where(LLMUsage.purpose == "optimize:rephrase"))
            .scalars()
            .all()
        )
        assert len(usage) == 1


def test_compile_raises_on_insufficient_data():
    engine = _engine()
    _seed(engine, n=1)
    cfg = OptimizationConfig(min_examples_to_compile=20)
    with pytest.raises(InsufficientDataError):
        compile_challenger(
            engine,
            strategy="rephrase",
            config=cfg,
            lm=_dummy_lm(),
            now=datetime(2026, 6, 9),
        )


def test_compile_rejects_invalid_challenger_but_records_spend():
    engine = _engine()
    _seed(engine, n=6)
    cfg = OptimizationConfig(
        min_examples_to_compile=2,
        max_bootstrapped_demos=2,
        val_fraction=0.34,
        validity_min_pass_rate=0.9,
    )
    # Every generation is empty -> invalid -> gate fails.
    bad_lm = DummyLM([{"question": "", "answer": ""} for _ in range(100)])
    with pytest.raises(OptimizationError):
        compile_challenger(
            engine,
            strategy="rephrase",
            config=cfg,
            lm=bad_lm,
            now=datetime(2026, 6, 9, 12, 0, 0),
        )
    with Session(engine) as s:
        challengers = (
            s.execute(select(PromptVersion).where(PromptVersion.status == "challenger"))
            .scalars()
            .all()
        )
        assert challengers == []  # rejected challenger NOT persisted
        usage = (
            s.execute(select(LLMUsage).where(LLMUsage.purpose == "optimize:rephrase"))
            .scalars()
            .all()
        )
        assert len(usage) == 1  # spend still recorded despite rejection


def test_compile_rejects_unknown_optimizer():
    engine = _engine()
    _seed(engine, n=2)
    cfg = OptimizationConfig(min_examples_to_compile=1, optimizer="mipro")
    with pytest.raises(OptimizationError, match="optimizer"):
        compile_challenger(
            engine,
            strategy="rephrase",
            config=cfg,
            lm=_dummy_lm(),
            now=datetime(2026, 6, 9),
        )
