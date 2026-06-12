"""CoreChangeLog: append-only audit of core-hash transitions per card."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class CoreChangeLog(Base):
    __tablename__ = "core_change_log"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    card_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    change_kind: Mapped[str] = mapped_column(String, nullable=False)
    old_hash: Mapped[str | None] = mapped_column(String, nullable=True)
    new_hash: Mapped[str] = mapped_column(String, nullable=False)
    old_normalized: Mapped[str | None] = mapped_column(String, nullable=True)
    new_normalized: Mapped[str] = mapped_column(String, nullable=False)
    detected_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
