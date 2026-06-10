"""Integration test for the mnemonic-optimize CLI (DummyLM, no network)."""

from __future__ import annotations

from datetime import datetime

from dspy.utils.dummies import DummyLM
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from mnemonic.cli.optimize import run_optimize
from mnemonic.config import OptimizationConfig
from mnemonic.db.models import Base, PromptVersion, TrainingExample


def _engine_path(tmp_path):
    db = tmp_path / "state.sqlite"
    engine = create_engine(f"sqlite:///{db}", future=True)
    Base.metadata.create_all(engine)
    return engine


def test_run_optimize_creates_challenger(tmp_path):
    engine = _engine_path(tmp_path)
    with Session(engine) as s:
        s.add(PromptVersion(
            id="pv-r", strategy="rephrase", version_no=0,
            instruction_text="Rephrase.", demos="[]", status="champion",
            parent_version_id=None, compiled_from_n_examples=None,
            created_at=datetime(2026, 6, 1),
        ))
        for i in range(4):
            s.add(TrainingExample(
                id=f"te{i}", card_id=f"c{i}", variation_id=f"v{i}",
                prompt_version_id="pv-r", base_q=f"What is X{i}?", base_a="Y.",
                variation_q=f"q{i}", variation_a=f"a{i}", label=1, reward=0.6,
                maturity=3, finalized=True, rating=None, note_context="ctx",
                created_at=datetime(2026, 6, 1),
            ))
        s.commit()

    cfg = OptimizationConfig(min_examples_to_compile=2, max_bootstrapped_demos=2,
                             val_fraction=0.34, validity_min_pass_rate=0.5)
    lm = DummyLM([{"question": f"gen q{i}", "answer": f"gen a{i}"} for i in range(40)])

    challenger = run_optimize(
        engine=engine, strategy="rephrase", config=cfg, lm=lm,
        now=datetime(2026, 6, 9, 12, 0, 0),
    )
    assert challenger.status == "challenger"
    assert challenger.version_no == 1
