from datetime import datetime, timedelta
from pathlib import Path

import pytest

from mnemonic.db.models import Base, LLMUsage
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.exceptions import LLMBudgetExceededError
from mnemonic.llm.budget import BudgetGuard


def _seed(engine, ts: datetime, cost: int):
    with session_scope(engine) as s:
        s.add(
            LLMUsage(
                id=f"u-{ts.isoformat()}",
                timestamp=ts,
                model="m",
                purpose="p",
                input_tokens=0,
                output_tokens=0,
                cost_millicents=cost,
            )
        )


def test_under_budget_allows(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    guard = BudgetGuard(engine=engine, daily_cents=25, monthly_cents=500)
    guard.assert_within_budget()  # no rows; passes


def test_over_daily_raises(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    _seed(engine, datetime.now(), 26_000)  # 26 cents = 26_000 millicents
    guard = BudgetGuard(engine=engine, daily_cents=25, monthly_cents=500)
    with pytest.raises(LLMBudgetExceededError) as ei:
        guard.assert_within_budget()
    assert ei.value.scope == "daily"


def test_over_monthly_raises(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    for i in range(1, 25):
        _seed(engine, datetime.now() - timedelta(days=i), 21_000)
    guard = BudgetGuard(engine=engine, daily_cents=25, monthly_cents=500)
    with pytest.raises(LLMBudgetExceededError) as ei:
        guard.assert_within_budget()
    assert ei.value.scope == "monthly"
