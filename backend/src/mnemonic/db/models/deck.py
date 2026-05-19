"""Deck model for Mnemonic.

Represents a collection of cards for a specific user, with deck-level
configuration for variation frequency, leech thresholds, and daily limits.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.card import Card
    from mnemonic.db.models.user import User

# FSRS and deck configuration defaults
DEFAULT_VARIATION_FREQUENCY = 0.5
DEFAULT_LEECH_THRESHOLD = 8


class Deck(Base):
    """Deck model.

    Attributes:
        id: Unique deck identifier (UUID).
        user_id: Foreign key to the user who owns this deck.
        name: Deck name.
        description: Deck description.
        variation_enabled: Whether question variations are enabled for this deck.
        variation_frequency: Float 0-1 indicating frequency of variations.
        leech_threshold: Number of reviews before a card is marked as leech.
        daily_review_limit: Maximum cards to review daily (nullable).
        daily_new_limit: Maximum new cards to learn daily (nullable).
        created_at: Timestamp when deck was created.
        updated_at: Timestamp when deck was last updated.
        user: Relationship to the user who owns this deck.
        cards: Relationship to cards in this deck.
    """

    __tablename__ = "deck"

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
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    variation_enabled: Mapped[bool] = mapped_column(default=True)
    variation_frequency: Mapped[float] = mapped_column(Float, default=DEFAULT_VARIATION_FREQUENCY)
    leech_threshold: Mapped[int] = mapped_column(Integer, default=DEFAULT_LEECH_THRESHOLD)
    daily_review_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    daily_new_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
        onupdate=func.now(),
    )

    # Relationships
    user: Mapped["User"] = Relationship(
        back_populates="decks",
    )
    cards: Mapped[list["Card"]] = Relationship(
        back_populates="deck",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of Deck."""
        return f"<Deck(id={self.id}, name={self.name}, user_id={self.user_id})>"
