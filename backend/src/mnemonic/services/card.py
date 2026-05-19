"""Card service for business logic.

Provides service layer for card operations including CRUD, validation,
and ownership verification.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from mnemonic.db.models.card import Card
from mnemonic.db.models.card_type import CardType
from mnemonic.db.models.deck import Deck
from mnemonic.db.repositories.card import CardRepository
from mnemonic.db.repositories.deck import DeckRepository
from mnemonic.exceptions import CardNotFoundError, DeckNotFoundError, ValidationError


class CardService:
    """Service for card operations.

    Handles CRUD operations, validation, and ownership verification for cards.
    """

    def __init__(self, card_repo: CardRepository, deck_repo: DeckRepository) -> None:
        """Initialize CardService with repositories.

        Args:
            card_repo: Repository for card data access.
            deck_repo: Repository for deck data access.
        """
        self.card_repo = card_repo
        self.deck_repo = deck_repo

    def create_card(
        self,
        session: Session,
        user_id: uuid.UUID,
        deck_id: uuid.UUID,
        content: str,
        card_type_id: uuid.UUID,
        notes: str = "",
        tags: list[str] | None = None,
    ) -> Card:
        """Create a new card in a deck.

        Validates all input before creating the card. Ensures user owns the deck
        and the card type exists.

        Args:
            session: SQLAlchemy session.
            user_id: ID of the user creating the card.
            deck_id: ID of the deck to add the card to.
            content: Card content in Markdown with shortcodes (required, 1-10000 chars).
            card_type_id: ID of the card type template (required).
            notes: User notes for the card (optional, max 5000 characters).
            tags: Tags for filtering and organization (optional).

        Returns:
            Created Card instance with FSRS defaults initialized.

        Raises:
            DeckNotFoundError: If deck doesn't exist.
            PermissionError: If user doesn't own the deck.
            ValidationError: If content is empty, card_type is invalid, or other validation fails.
        """
        tags = tags or []

        # Validate content
        if not content or not isinstance(content, str) or len(content.strip()) == 0:
            raise ValidationError("Card content is required and must not be empty")

        if len(content) > 10000:
            raise ValidationError("Card content must be at most 10000 characters")

        # Validate notes if provided
        if notes and len(notes) > 5000:
            raise ValidationError("Card notes must be at most 5000 characters")

        # Verify deck exists and user owns it
        try:
            deck = self.deck_repo.get(session, deck_id)
        except Exception as e:
            raise DeckNotFoundError(f"Deck with id {deck_id} not found") from e

        if deck.user_id != user_id:
            raise PermissionError("User does not own this deck")

        # Verify card_type exists
        card_type = session.query(CardType).filter(CardType.id == card_type_id).first()
        if card_type is None:
            raise ValidationError(f"Card type with id {card_type_id} not found")

        # Create card with FSRS defaults
        card = self.card_repo.create(
            session,
            deck_id=deck_id,
            card_type_id=card_type_id,
            content=content,
            notes=notes,
            tags=tags,
        )

        return card

    def get_deck_cards(
        self,
        session: Session,
        user_id: uuid.UUID,
        deck_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Card]:
        """Get all cards in a deck with pagination.

        Verifies user owns the deck before returning cards.

        Args:
            session: SQLAlchemy session.
            user_id: ID of the user requesting the cards.
            deck_id: ID of the deck to get cards from.
            skip: Number of cards to skip (default 0).
            limit: Maximum number of cards to return (default 100).

        Returns:
            List of Card entities in the deck.

        Raises:
            DeckNotFoundError: If deck doesn't exist.
            PermissionError: If user doesn't own the deck.
        """
        # Verify deck exists and user owns it
        try:
            deck = self.deck_repo.get(session, deck_id)
        except Exception as e:
            raise DeckNotFoundError(f"Deck with id {deck_id} not found") from e

        if deck.user_id != user_id:
            raise PermissionError("User does not own this deck")

        return self.card_repo.get_by_deck(session, deck_id, skip=skip, limit=limit)

    def get_card(
        self,
        session: Session,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Card:
        """Get a card by ID, ensuring user owns the deck.

        Args:
            session: SQLAlchemy session.
            card_id: ID of the card to retrieve.
            user_id: ID of the user requesting the card.

        Returns:
            The Card instance.

        Raises:
            CardNotFoundError: If card doesn't exist.
            PermissionError: If user doesn't own the card's deck.
        """
        try:
            card = self.card_repo.get(session, card_id)
        except Exception as e:
            raise CardNotFoundError(f"Card with id {card_id} not found") from e

        # Verify ownership by checking deck
        deck = session.query(Deck).filter(Deck.id == card.deck_id).first()
        if deck is None or deck.user_id != user_id:
            raise PermissionError("User does not own this card's deck")

        return card

    def update_card(
        self,
        session: Session,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates: Any,
    ) -> Card:
        """Update a card, verifying ownership.

        Args:
            session: SQLAlchemy session.
            card_id: ID of the card to update.
            user_id: ID of the user requesting the update.
            **updates: Fields to update (content, notes, tags, suspended).

        Returns:
            The updated Card instance.

        Raises:
            CardNotFoundError: If card doesn't exist.
            PermissionError: If user doesn't own the card's deck.
            ValidationError: If update data is invalid.
        """
        # Verify ownership first (raises if not found or not owned)
        self.get_card(session, card_id, user_id)

        # Validate any updates
        if "content" in updates and updates["content"] is not None:
            content = updates["content"]
            if not content or not isinstance(content, str) or len(content.strip()) == 0:
                raise ValidationError("Card content is required and must not be empty")
            if len(content) > 10000:
                raise ValidationError("Card content must be at most 10000 characters")

        if "notes" in updates and updates["notes"] is not None:
            notes = updates["notes"]
            if len(notes) > 5000:
                raise ValidationError("Card notes must be at most 5000 characters")

        # Remove None values from updates
        updates = {k: v for k, v in updates.items() if v is not None}

        # Update card
        return self.card_repo.update(session, card_id, **updates)

    def delete_card(
        self,
        session: Session,
        card_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete a card, verifying ownership.

        Args:
            session: SQLAlchemy session.
            card_id: ID of the card to delete.
            user_id: ID of the user requesting deletion.

        Raises:
            CardNotFoundError: If card doesn't exist.
            PermissionError: If user doesn't own the card's deck.
        """
        # Verify ownership first (raises if not found or not owned)
        self.get_card(session, card_id, user_id)

        # Delete the card
        self.card_repo.delete(session, card_id)
