"""Daily/monthly LLM cost cap. Reads aggregates from LLMUsage rows."""

from __future__ import annotations

from datetime import datetime, timedelta

from sqlalchemy import Engine, func

from mnemonic.db.models import LLMUsage
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import LLMBudgetExceededError


class BudgetGuard:
    """Check if LLM costs are within daily/monthly budget limits."""

    def __init__(self, *, engine: Engine, daily_cents: int, monthly_cents: int) -> None:
        """Initialize BudgetGuard with budget caps.

        Args:
            engine: SQLAlchemy engine for database access.
            daily_cents: Daily budget cap in cents.
            monthly_cents: Monthly budget cap in cents.
        """
        self.engine = engine
        self.daily_millicents = daily_cents * 1000
        self.monthly_millicents = monthly_cents * 1000

    def _sum_since(self, since: datetime) -> int:
        """Sum all costs from a given timestamp onward.

        Args:
            since: Datetime from which to sum costs.

        Returns:
            Total cost in millicents since the given time.
        """
        with session_scope(self.engine) as s:
            total = (
                s.query(func.coalesce(func.sum(LLMUsage.cost_millicents), 0))
                .filter(LLMUsage.timestamp >= since)
                .scalar()
            )
            return int(total or 0)

    def assert_within_budget(self) -> None:
        """Check if costs are within budget limits.

        Raises:
            LLMBudgetExceededError: If daily or monthly budget is exceeded.
        """
        now = datetime.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        month_start = day_start - timedelta(days=30)

        daily_spent = self._sum_since(day_start)
        if daily_spent >= self.daily_millicents:
            raise LLMBudgetExceededError(
                spent_millicents=daily_spent,
                cap_millicents=self.daily_millicents,
                scope="daily",
            )

        monthly_spent = self._sum_since(month_start)
        if monthly_spent >= self.monthly_millicents:
            raise LLMBudgetExceededError(
                spent_millicents=monthly_spent,
                cap_millicents=self.monthly_millicents,
                scope="monthly",
            )
