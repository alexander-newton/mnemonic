"""User model for Mnemonic.

Represents a user of the spaced repetition system with their configuration,
preferences, and FSRS parameters.
"""

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSON, UUID
from sqlalchemy.orm import Mapped, Relationship, mapped_column

from mnemonic.db.models.base import Base

if False:
    from mnemonic.db.models.deck import Deck


class User(Base):
    """User model.

    Attributes:
        id: Unique user identifier (UUID).
        email: User's email address (unique, indexed).
        password_hash: Hashed password.
        fsrs_params: JSON object containing per-user FSRS optimization parameters.
        settings: JSON object containing user preferences.
        created_at: Timestamp when user was created.
        updated_at: Timestamp when user was last updated.
        decks: Relationship to user's decks.
    """

    __tablename__ = "user"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
    )
    password_hash: Mapped[str] = mapped_column(Text)
    fsrs_params: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
    )
    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        default=dict,
    )
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
    decks: Mapped[list["Deck"]] = Relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        """Return string representation of User."""
        return f"<User(id={self.id}, email={self.email})>"
