"""TrainingExample model for Mnemonic.

Stores training data for DSPy to optimize LLM prompts based on user feedback.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.card import Card


class TrainingExample(Base):
    """TrainingExample model.

    Attributes:
        id: Unique training example identifier (UUID).
        card_id: Foreign key to the card this example is for.
        original_content: Original card content.
        varied_content: The variation generated from the original.
        user_feedback: JSON object containing user feedback on the variation.
        created_at: Timestamp when example was created.
        card: Relationship to the parent card.
    """

    __tablename__ = "training_example"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    card_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("card.id", ondelete="CASCADE"),
        index=True,
    )
    original_content: Mapped[str] = mapped_column(Text)
    varied_content: Mapped[str] = mapped_column(Text)
    user_feedback: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
    )

    # Relationships
    card: Mapped["Card"] = Relationship(
        back_populates="training_examples",
    )

    def __repr__(self) -> str:
        """Return string representation of TrainingExample."""
        return f"<TrainingExample(id={self.id}, card_id={self.card_id})>"
