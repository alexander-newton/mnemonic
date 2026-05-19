"""ReviewLog model for Mnemonic.

Records each review session, including ratings, timing, and FSRS state changes.
"""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base
from mnemonic.db.models.card import CardState

if False:
    from mnemonic.db.models.card import Card
    from mnemonic.db.models.user import User


class ReviewLog(Base):
    """ReviewLog model.

    Attributes:
        id: Unique review log identifier (UUID).
        card_id: Foreign key to the card being reviewed.
        user_id: Foreign key to the user performing the review.
        rating: Review rating (1-4 per FSRS).
        response_time_ms: Time taken to respond in milliseconds.
        review_time: Timestamp of the review.
        state_before: Card state before review.
        state_after: Card state after review.
        stability_before: FSRS stability before review.
        stability_after: FSRS stability after review.
        difficulty_before: FSRS difficulty before review.
        difficulty_after: FSRS difficulty after review.
        variation_used: Whether a variation was shown.
        variation_id: UUID of the variation shown (if any).
        variation_helpful: User's feedback on variation helpfulness.
        card: Relationship to the reviewed card.
        user: Relationship to the user.
    """

    __tablename__ = "review_log"

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
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        index=True,
    )
    rating: Mapped[int] = mapped_column(Integer)
    response_time_ms: Mapped[int] = mapped_column(Integer)
    review_time: Mapped[datetime] = mapped_column(DateTime(timezone=False))
    state_before: Mapped[CardState | None] = mapped_column(
        SQLEnum(CardState),
        nullable=True,
    )
    state_after: Mapped[CardState | None] = mapped_column(
        SQLEnum(CardState),
        nullable=True,
    )
    stability_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    stability_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_before: Mapped[float | None] = mapped_column(Float, nullable=True)
    difficulty_after: Mapped[float | None] = mapped_column(Float, nullable=True)
    variation_used: Mapped[bool] = mapped_column(default=False)
    variation_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
    )
    variation_helpful: Mapped[bool | None] = mapped_column(nullable=True)

    # Relationships
    card: Mapped["Card"] = Relationship(
        back_populates="reviews",
    )
    user: Mapped["User"] = Relationship()

    def __repr__(self) -> str:
        """Return string representation of ReviewLog."""
        return f"<ReviewLog(id={self.id}, card_id={self.card_id}, rating={self.rating})>"
