"""SchedulingState model: FSRS state per card-block-id."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Float, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class SchedulingState(Base):
    __tablename__ = "scheduling_state"

    card_id: Mapped[str] = mapped_column(String, primary_key=True)
    state: Mapped[str] = mapped_column(String, nullable=False, default="new")
    stability: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    difficulty: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    due: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    reps: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    lapses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    leech_score: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    leech_notified: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    suspended: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    parent_card_id: Mapped[str | None] = mapped_column(String, nullable=True)
    orphan: Mapped[bool] = mapped_column(Integer, nullable=False, default=0)
    core_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    core_hash_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    cloze_signature: Mapped[str | None] = mapped_column(String, nullable=True)
    core_changed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    core_changed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.current_timestamp(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        nullable=False,
    )
