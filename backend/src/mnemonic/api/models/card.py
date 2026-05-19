"""Pydantic models for card API.

Defines request and response schemas for card CRUD endpoints.
"""

import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class CreateCardRequest(BaseModel):
    """Request body for card creation.

    Attributes:
        content: Card content in Markdown with shortcodes (1-10000 characters).
        card_type_id: ID of the card type template to use.
        notes: Optional user notes for the card (max 5000 characters).
        tags: Optional tags for filtering and organization.
    """

    content: str = Field(min_length=1, max_length=10000)
    card_type_id: uuid.UUID
    notes: str = Field(default="", max_length=5000)
    tags: list[str] = Field(default_factory=list)


class UpdateCardRequest(BaseModel):
    """Request body for card update.

    All fields are optional. Only provided fields will be updated.

    Attributes:
        content: Card content in Markdown with shortcodes (optional).
        notes: User notes for the card (optional).
        tags: Tags for filtering and organization (optional).
        suspended: Whether the card is suspended from reviews (optional).
    """

    content: str | None = Field(default=None, min_length=1, max_length=10000)
    notes: str | None = Field(default=None, max_length=5000)
    tags: list[str] | None = None
    suspended: bool | None = None


class CardResponse(BaseModel):
    """Card object returned in API responses.

    Attributes:
        id: Unique card identifier.
        deck_id: ID of the deck containing this card.
        card_type_id: ID of the card type template.
        content: Card content in Markdown with shortcodes.
        notes: User notes for this card.
        tags: Tags for filtering.
        state: FSRS state (new, learning, review, relearning).
        stability: FSRS stability parameter.
        difficulty: FSRS difficulty parameter.
        due: Next review time (nullable).
        reps: Number of times this card has been reviewed.
        lapses: Number of times this card has failed.
        suspended: Whether the card is suspended from reviews.
        created_at: When the card was created.
        updated_at: When the card was last updated.
    """

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    deck_id: uuid.UUID
    card_type_id: uuid.UUID
    content: str
    notes: str
    tags: list[str]
    state: str
    stability: float
    difficulty: float
    due: datetime | None
    reps: int
    lapses: int
    suspended: bool
    created_at: datetime
    updated_at: datetime
