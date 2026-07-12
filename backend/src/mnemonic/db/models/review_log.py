"""ReviewLog: append-only record of every card review."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class ReviewLog(Base):
    __tablename__ = "review_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    response_time_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    review_time: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    state_before: Mapped[str | None] = mapped_column(String, nullable=True)
    state_after: Mapped[str | None] = mapped_column(String, nullable=True)
    stability_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    variation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    variation_helpful: Mapped[int | None] = mapped_column(Integer, nullable=True)
    deck_folder: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (Index("idx_review_log_deck_time", "deck_folder", "review_time"),)
