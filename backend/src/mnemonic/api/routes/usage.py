"""LLM usage telemetry endpoint."""

from __future__ import annotations

from datetime import datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import func

from mnemonic.api.deps import get_engine
from mnemonic.db.models import LLMUsage
from mnemonic.db.sqlite import session_scope

router = APIRouter(prefix="/usage", tags=["usage"])


@router.get("")
def usage_summary(engine=Depends(get_engine)):
    now = datetime.now()
    day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = day_start - timedelta(days=30)
    with session_scope(engine) as s:
        daily = int(s.query(func.coalesce(func.sum(LLMUsage.cost_millicents), 0))
                    .filter(LLMUsage.timestamp >= day_start).scalar() or 0)
        monthly = int(s.query(func.coalesce(func.sum(LLMUsage.cost_millicents), 0))
                      .filter(LLMUsage.timestamp >= month_start).scalar() or 0)
        cache_read = int(s.query(func.coalesce(func.sum(LLMUsage.cache_read_tokens), 0))
                         .filter(LLMUsage.timestamp >= day_start).scalar() or 0)
        total_input = int(s.query(func.coalesce(func.sum(LLMUsage.input_tokens), 0))
                          .filter(LLMUsage.timestamp >= day_start).scalar() or 0)
    hit_rate = (cache_read / total_input) if total_input else 0.0
    return {
        "daily_cents": daily / 1000,
        "monthly_cents": monthly / 1000,
        "cache_hit_rate": round(hit_rate, 3),
    }
