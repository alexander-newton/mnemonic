"""Card model for Mnemonic.

Represents an individual flashcard with FSRS scheduling state,
leech tracking, and content in Markdown with shortcodes.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.card_type import CardType
    from mnemonic.db.models.deck import Deck
    from mnemonic.db.models.review_log import ReviewLog
    from mnemonic.db.models.training_example import TrainingExample
    from mnemonic.db.models.variation_cache import VariationCache

# FSRS initial parameters
FSRS_INITIAL_STABILITY = 0.0
FSRS_INITIAL_DIFFICULTY = 5.0
INITIAL_LEECH_SCORE = 0.0


class CardState(str, Enum):
    """Enum for card learning state in FSRS algorithm."""

    NEW = "new"
    LEARNING = "learning"
    REVIEW = "review"
    RELEARNING = "relearning"


class Card(Base):
    """Card model.

    Attributes:
        id: Unique card identifier (UUID).
        deck_id: Foreign key to the deck containing this card.
        card_type_id: Foreign key to the card type template.
        content: Markdown content with shortcodes (front/back, cloze, etc.).
        notes: User's personal notes for this card.
        tags: JSON array of tags for filtering.
        state: FSRS state (new, learning, review, relearning).
        stability: FSRS stability parameter.
        difficulty: FSRS difficulty parameter.
        due: Due date for review (next review time).
        reps: Number of times this card has been reviewed.
        lapses: Number of times this card has been failed.
        leech_score: Leech score (higher = more problematic).
        leech_notified: Whether user has been notified this is a leech.
        parent_card_id: For card decomposition, reference to parent card.
        suspended: Whether this card is suspended from reviews.
        created_at: Timestamp when card was created.
        updated_at: Timestamp when card was last updated.
        deck: Relationship to the parent deck.
        card_type: Relationship to the card type template.
        reviews: Relationship to review history.
        variations: Relationship to cached variations.
        training_examples: Relationship to training examples.
    """

    __tablename__ = "card"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    deck_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("deck.id", ondelete="CASCADE"),
        index=True,
    )
    card_type_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("card_type.id", ondelete="RESTRICT"),
        index=True,
    )
    content: Mapped[str] = mapped_column(Text)
    notes: Mapped[str] = mapped_column(Text, default="")
    tags: Mapped[list[Any]] = mapped_column(JSON, default=list)
    state: Mapped[CardState] = mapped_column(SQLEnum(CardState), default=CardState.NEW)
    stability: Mapped[float] = mapped_column(Float, default=FSRS_INITIAL_STABILITY)
    difficulty: Mapped[float] = mapped_column(Float, default=FSRS_INITIAL_DIFFICULTY)
    due: Mapped[datetime | None] = mapped_column(DateTime(timezone=False), nullable=True)
    reps: Mapped[int] = mapped_column(Integer, default=0)
    lapses: Mapped[int] = mapped_column(Integer, default=0)
    leech_score: Mapped[float] = mapped_column(Float, default=INITIAL_LEECH_SCORE)
    leech_notified: Mapped[bool] = mapped_column(default=False)
    parent_card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("card.id", ondelete="SET NULL"),
        nullable=True,
    )
    suspended: Mapped[bool] = mapped_column(default=False)
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
    deck: Mapped["Deck"] = Relationship(
        back_populates="cards",
    )
    card_type: Mapped["CardType"] = Relationship(
        back_populates="cards",
    )
    reviews: Mapped[list["ReviewLog"]] = Relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    variations: Mapped[list["VariationCache"]] = Relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )
    training_examples: Mapped[list["TrainingExample"]] = Relationship(
        back_populates="card",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of Card."""
        return f"<Card(id={self.id}, deck_id={self.deck_id}, state={self.state})>"
