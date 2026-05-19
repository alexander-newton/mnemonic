"""Pydantic models for deck API.

Defines request and response schemas for deck CRUD endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateDeckRequest(BaseModel):
    """Request body for deck creation.

    Attributes:
        name: Deck name (1-200 characters).
        description: Deck description (optional, max 1000 characters).
        variation_enabled: Whether question variations are enabled (default True).
        variation_frequency: Frequency of variations 0.0-1.0 (default 0.5).
        leech_threshold: Number of reviews before card marked as leech (default 8, min 1).
        daily_review_limit: Maximum cards to review daily (optional).
        daily_new_limit: Maximum new cards to learn daily (optional).
    """

    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    variation_enabled: bool = Field(default=True)
    variation_frequency: float = Field(default=0.5, ge=0.0, le=1.0)
    leech_threshold: int = Field(default=8, ge=1)
    daily_review_limit: int | None = Field(default=None, ge=1)
    daily_new_limit: int | None = Field(default=None, ge=1)


class UpdateDeckRequest(BaseModel):
    """Request body for deck update.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        name: Deck name (optional, 1-200 characters if provided).
        description: Deck description (optional, max 1000 characters).
        variation_enabled: Whether question variations are enabled (optional).
        variation_frequency: Frequency of variations 0.0-1.0 (optional).
        leech_threshold: Number of reviews before card marked as leech (optional, min 1).
        daily_review_limit: Maximum cards to review daily (optional).
        daily_new_limit: Maximum new cards to learn daily (optional).
    """

    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    variation_enabled: bool | None = None
    variation_frequency: float | None = Field(default=None, ge=0.0, le=1.0)
    leech_threshold: int | None = Field(default=None, ge=1)
    daily_review_limit: int | None = Field(default=None, ge=1)
    daily_new_limit: int | None = Field(default=None, ge=1)


class DeckResponse(BaseModel):
    """Deck object returned in API responses.

    Attributes:
        id: Unique deck identifier.
        user_id: ID of the user who owns this deck.
        name: Deck name.
        description: Deck description.
        variation_enabled: Whether question variations are enabled.
        variation_frequency: Frequency of variations.
        leech_threshold: Number of reviews before card marked as leech.
        daily_review_limit: Maximum cards to review daily (nullable).
        daily_new_limit: Maximum new cards to learn daily (nullable).
        created_at: When the deck was created.
        updated_at: When the deck was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    user_id: uuid.UUID
    name: str
    description: str
    variation_enabled: bool
    variation_frequency: float
    leech_threshold: int
    daily_review_limit: int | None
    daily_new_limit: int | None
    created_at: datetime
    updated_at: datetime
