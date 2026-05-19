"""Card repository for data access.

Provides data access operations for Card entities including filtering by state,
leech detection, suspension management, and review scheduling queries.
"""

import uuid
from datetime import datetime

from sqlalchemy import and_
from sqlalchemy.orm import Session

from mnemonic.db.models.card import Card, CardState
from mnemonic.db.models.deck import Deck
from mnemonic.db.repositories.base import BaseRepository
from mnemonic.exceptions import CardNotFoundError


class CardRepository(BaseRepository[Card]):
    """Repository for Card entities.

    Extends BaseRepository with Card-specific query methods.
    """

    def __init__(self) -> None:
        """Initialize CardRepository with Card model."""
        super().__init__(Card)

    def get_by_deck(
        self,
        session: Session,
        deck_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Card]:
        """Get all cards in a deck with pagination.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of deck to get cards for.
            skip: Number of cards to skip (default 0).
            limit: Maximum number of cards to return (default 100).

        Returns:
            List of Card entities in the deck.
        """
        return session.query(Card).filter(Card.deck_id == deck_id).offset(skip).limit(limit).all()

    def get_due_for_review(
        self,
        session: Session,
        user_id: uuid.UUID,
        limit: int = 50,
    ) -> list[Card]:
        """Get cards due for review for a user.

        Cards are due when their due date is on or before now.

        Args:
            session: SQLAlchemy session.
            user_id: ID of user to get due cards for.
            limit: Maximum number of cards to return (default 50).

        Returns:
            List of Card entities due for review.
        """
        now = datetime.utcnow()
        return (
            session.query(Card)
            .join(Deck, Card.deck_id == Deck.id)
            .filter(
                and_(
                    Card.due <= now,
                    ~Card.suspended,
                    Deck.user_id == user_id,
                )
            )
            .limit(limit)
            .all()
        )

    def get_by_state(
        self,
        session: Session,
        deck_id: uuid.UUID,
        state: CardState,
    ) -> list[Card]:
        """Get all cards in a deck with a specific learning state.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of deck to filter.
            state: CardState to filter by (new, learning, review, relearning).

        Returns:
            List of Card entities with the specified state.
        """
        return session.query(Card).filter(and_(Card.deck_id == deck_id, Card.state == state)).all()

    def get_leeches(
        self,
        session: Session,
        deck_id: uuid.UUID,
        threshold: int = 8,
    ) -> list[Card]:
        """Get cards with high leech scores in a deck.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of deck to search.
            threshold: Leech score threshold (default 8).

        Returns:
            List of Card entities with leech_score >= threshold.
        """
        return (
            session.query(Card)
            .filter(
                and_(
                    Card.deck_id == deck_id,
                    Card.leech_score >= threshold,
                )
            )
            .all()
        )

    def suspend(self, session: Session, card_id: uuid.UUID) -> Card:
        """Mark a card as suspended from reviews.

        Args:
            session: SQLAlchemy session.
            card_id: ID of card to suspend.

        Returns:
            The updated Card entity.

        Raises:
            CardNotFoundError: If card is not found.
        """
        card = session.query(Card).filter(Card.id == card_id).first()
        if card is None:
            raise CardNotFoundError(f"Card with id {card_id} not found")

        card.suspended = True
        session.commit()
        return card

    def unsuspend(self, session: Session, card_id: uuid.UUID) -> Card:
        """Remove suspension from a card.

        Args:
            session: SQLAlchemy session.
            card_id: ID of card to unsuspend.

        Returns:
            The updated Card entity.

        Raises:
            CardNotFoundError: If card is not found.
        """
        card = session.query(Card).filter(Card.id == card_id).first()
        if card is None:
            raise CardNotFoundError(f"Card with id {card_id} not found")

        card.suspended = False
        session.commit()
        return card
