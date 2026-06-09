"""Integration test for the mnemonic-label CLI."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import create_engine as sa_create_engine
from sqlalchemy.orm import Session

from mnemonic.cli.label import run_labeling
from mnemonic.config import OptimizationConfig
from mnemonic.db.models import Base, PromptVersion


def test_run_labeling_seeds_champions_and_reports(tmp_path):
    from pathlib import Path

    from mnemonic.llm.prompts import variation as variation_pkg

    prompts_dir = Path(variation_pkg.__file__).parent

    db_path = tmp_path / "state.sqlite"
    engine = sa_create_engine(f"sqlite:///{db_path}", future=True)
    Base.metadata.create_all(engine)
    engine.dispose()

    report = run_labeling(
        db_path=db_path,
        prompts_dir=prompts_dir,
        config=OptimizationConfig(),
        now=datetime(2026, 6, 9, 12, 0, 0),
    )

    assert report.labeled == 0  # no variations yet
    check_engine = sa_create_engine(f"sqlite:///{db_path}", future=True)
    with Session(check_engine) as s:
        assert s.query(PromptVersion).count() == 3
