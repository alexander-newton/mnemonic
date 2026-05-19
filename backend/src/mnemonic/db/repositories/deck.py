"""Deck repository for data access.

Provides data access operations for Deck entities with user-specific queries,
card count statistics, and configuration updates.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from mnemonic.db.models.deck import Deck
from mnemonic.db.repositories.base import BaseRepository
from mnemonic.exceptions import DeckNotFoundError


class DeckRepository(BaseRepository[Deck]):
    """Repository for Deck entities.

    Extends BaseRepository with Deck-specific query methods.
    """

    def __init__(self) -> None:
        """Initialize DeckRepository with Deck model."""
        super().__init__(Deck)

    def get_by_user(
        self,
        session: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Deck]:
        """Get all decks for a user with pagination.

        Args:
            session: SQLAlchemy session.
            user_id: ID of user to get decks for.
            skip: Number of decks to skip (default 0).
            limit: Maximum number of decks to return (default 100).

        Returns:
            List of Deck entities for the user.
        """
        return session.query(Deck).filter(Deck.user_id == user_id).offset(skip).limit(limit).all()

    def get_with_card_counts(
        self,
        session: Session,
        deck_id: uuid.UUID,
    ) -> Deck:
        """Get a deck with its card collection loaded.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of deck to retrieve.

        Returns:
            The Deck entity with cards relationship loaded.

        Raises:
            DeckNotFoundError: If deck is not found.
        """
        deck = session.query(Deck).filter(Deck.id == deck_id).first()
        if deck is None:
            raise DeckNotFoundError(f"Deck with id {deck_id} not found")
        return deck

    def update_settings(
        self,
        session: Session,
        deck_id: uuid.UUID,
        **kwargs: Any,
    ) -> Deck:
        """Update deck configuration settings.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of deck to update.
            **kwargs: Configuration keys and values to update.

        Returns:
            The updated Deck entity.

        Raises:
            DeckNotFoundError: If deck is not found.
        """
        deck = session.query(Deck).filter(Deck.id == deck_id).first()
        if deck is None:
            raise DeckNotFoundError(f"Deck with id {deck_id} not found")

        for key, value in kwargs.items():
            if hasattr(deck, key):
                setattr(deck, key, value)

        session.commit()
        return deck
