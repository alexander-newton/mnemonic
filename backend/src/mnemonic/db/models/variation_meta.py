"""VariationMeta: metadata for an LLM-generated variation written to a note."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class VariationMeta(Base):
    __tablename__ = "variation_meta"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    model: Mapped[str] = mapped_column(String, nullable=False)
    generated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    shown_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    helpful_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    content_hash: Mapped[str] = mapped_column(String, nullable=False)
    note_path: Mapped[str] = mapped_column(String, nullable=False)
    prompt_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    arm: Mapped[str] = mapped_column(String, nullable=False, default="none")
    invalidated_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
