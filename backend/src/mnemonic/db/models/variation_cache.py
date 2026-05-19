"""VariationCache model for Mnemonic.

Caches generated question variations with their quality metrics and user feedback.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.card import Card


class VariationCache(Base):
    """VariationCache model.

    Attributes:
        id: Unique variation cache identifier (UUID).
        card_id: Foreign key to the card this variation is for.
        varied_content: The generated variation content.
        model_used: Name of the LLM model used to generate the variation.
        prompt_version: Version of the prompt template used.
        semantic_similarity: Semantic similarity score to original (0-1).
        lexical_difference: Lexical difference score to original (0-1).
        times_shown: Number of times this variation has been shown.
        times_correct: Number of times the user answered correctly with this variation.
        user_ratings: JSON array of user ratings for this variation.
        created_at: Timestamp when variation was generated.
        card: Relationship to the parent card.
    """

    __tablename__ = "variation_cache"

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
    varied_content: Mapped[str] = mapped_column(Text)
    model_used: Mapped[str] = mapped_column(String(255))
    prompt_version: Mapped[str | None] = mapped_column(String(255), nullable=True)
    semantic_similarity: Mapped[float | None] = mapped_column(Float, nullable=True)
    lexical_difference: Mapped[float | None] = mapped_column(Float, nullable=True)
    times_shown: Mapped[int] = mapped_column(Integer, default=0)
    times_correct: Mapped[int] = mapped_column(Integer, default=0)
    user_ratings: Mapped[list[Any]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=False),
        server_default=func.now(),
    )

    # Relationships
    card: Mapped["Card"] = Relationship(
        back_populates="variations",
    )

    def __repr__(self) -> str:
        """Return string representation of VariationCache."""
        return (
            f"<VariationCache(id={self.id}, card_id={self.card_id}, model_used={self.model_used})>"
        )
