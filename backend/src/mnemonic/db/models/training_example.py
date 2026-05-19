"""TrainingExample: labelled variation outputs used for DSPy optimisation."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class TrainingExample(Base):
    __tablename__ = "training_example"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False)
    variation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    base_q: Mapped[str] = mapped_column(Text, nullable=False)
    base_a: Mapped[str] = mapped_column(Text, nullable=False)
    variation_q: Mapped[str] = mapped_column(Text, nullable=False)
    variation_a: Mapped[str] = mapped_column(Text, nullable=False)
    label: Mapped[int] = mapped_column(Integer, nullable=False)
    rating: Mapped[int | None] = mapped_column(Integer, nullable=True)
    note_context: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
