"""CardType model for Mnemonic.

Represents a template for card format, including field definitions,
rendering pipeline, and syntax type.
"""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.card import Card


class SyntaxType(str, Enum):
    """Enum for card syntax types."""

    FRONTBACK = "frontback"
    CLOZE = "cloze"
    IMAGE_CLOZE = "image_cloze"
    CUSTOM = "custom"


class CardType(Base):
    """CardType model.

    Attributes:
        id: Unique card type identifier (UUID).
        user_id: Foreign key to user (nullable for builtin types).
        name: Card type name.
        description: Card type description.
        parent_type_id: Self-referential foreign key for inheritance.
        syntax_type: Enum indicating card syntax (frontback, cloze, image_cloze, custom).
        fields: JSON array defining fields for this card type.
        render_pipeline: JSON array of rendering steps (e.g., ["pandoc", "mathjax"]).
        is_builtin: Whether this is a builtin type or user-created.
        created_at: Timestamp when card type was created.
        updated_at: Timestamp when card type was last updated.
        parent_type: Self-referential relationship to parent type.
        cards: Relationship to cards using this type.
    """

    __tablename__ = "card_type"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("user.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text, default="")
    parent_type_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("card_type.id", ondelete="SET NULL"),
        nullable=True,
    )
    syntax_type: Mapped[SyntaxType] = mapped_column(SQLEnum(SyntaxType))
    fields: Mapped[list[Any]] = mapped_column(JSON, default=list)
    render_pipeline: Mapped[list[Any]] = mapped_column(JSON, default=list)
    is_builtin: Mapped[bool] = mapped_column(default=False)
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
    parent_type: Mapped["CardType | None"] = Relationship(
        "CardType",
        remote_side=[id],
        foreign_keys=[parent_type_id],
        back_populates="child_types",
    )
    child_types: Mapped[list["CardType"]] = Relationship(
        "CardType",
        back_populates="parent_type",
        cascade="all, delete-orphan",
    )
    cards: Mapped[list["Card"]] = Relationship(
        "Card",
        back_populates="card_type",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of CardType."""
        return f"<CardType(id={self.id}, name={self.name}, syntax_type={self.syntax_type})>"
