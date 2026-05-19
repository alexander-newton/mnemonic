"""LLMUsage model for Mnemonic.

Tracks token and cost metrics for LLM API usage per user per day.
"""

import uuid
from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.user import User


class LLMUsage(Base):
    """LLMUsage model.

    Attributes:
        id: Unique LLM usage record identifier (UUID).
        user_id: Foreign key to the user.
        date: Date of usage.
        model: LLM model name used (e.g., "gpt-4", "gpt-3.5-turbo").
        tokens_in: Number of input tokens used.
        tokens_out: Number of output tokens generated.
        cost_usd: Total cost in USD.
        user: Relationship to the user.
    """

    __tablename__ = "llm_usage"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, index=True)
    model: Mapped[str] = mapped_column(String(255))
    tokens_in: Mapped[int] = mapped_column(Integer, default=0)
    tokens_out: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=4),
        nullable=True,
    )

    # Relationships
    user: Mapped["User"] = Relationship()

    def __repr__(self) -> str:
        """Return string representation of LLMUsage."""
        return f"<LLMUsage(id={self.id}, user_id={self.user_id}, date={self.date}, model={self.model})>"
