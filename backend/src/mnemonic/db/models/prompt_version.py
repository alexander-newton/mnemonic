"""PromptVersion: a versioned, per-strategy variation prompt in the registry."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from mnemonic.db.models.base import Base


class PromptVersion(Base):
    __tablename__ = "prompt_version"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    strategy: Mapped[str] = mapped_column(String, nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False)
    instruction_text: Mapped[str] = mapped_column(Text, nullable=False)
    demos: Mapped[str] = mapped_column(Text, nullable=False, default="[]")
    status: Mapped[str] = mapped_column(String, nullable=False, default="challenger")
    parent_version_id: Mapped[str | None] = mapped_column(String, nullable=True)
    compiled_from_n_examples: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
