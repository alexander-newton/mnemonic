"""Deck service for business logic.

Provides service layer for deck operations including CRUD, validation,
and ownership verification.
"""

import uuid
from typing import Any

from sqlalchemy.orm import Session

from mnemonic.db.models.deck import Deck
from mnemonic.db.repositories.deck import DeckRepository
from mnemonic.exceptions import DeckNotFoundError, ValidationError


class DeckService:
    """Service for deck operations.

    Handles CRUD operations, validation, and ownership verification for decks.
    """

    def __init__(self, deck_repo: DeckRepository) -> None:
        """Initialize DeckService with a DeckRepository.

        Args:
            deck_repo: Repository for deck data access.
        """
        self.deck_repo = deck_repo

    def create_deck(
        self,
        session: Session,
        user_id: uuid.UUID,
        name: str,
        description: str = "",
        **settings: Any,
    ) -> Deck:
        """Create a new deck for a user.

        Validates all input before creating the deck.

        Args:
            session: SQLAlchemy session.
            user_id: ID of the user creating the deck.
            name: Deck name (required, 1-200 characters).
            description: Deck description (optional, max 1000 characters).
            **settings: Optional deck configuration (variation_enabled,
                variation_frequency, leech_threshold, daily_review_limit,
                daily_new_limit).

        Returns:
            Created Deck instance.

        Raises:
            ValidationError: If input validation fails.
        """
        # Validate name
        if not name or not isinstance(name, str) or len(name.strip()) == 0:
            raise ValidationError("Deck name is required and must not be empty")

        if len(name) > 200:
            raise ValidationError("Deck name must be at most 200 characters")

        # Validate description if provided
        if description and len(description) > 1000:
            raise ValidationError("Deck description must be at most 1000 characters")

        # Validate optional settings
        if "variation_frequency" in settings and settings["variation_frequency"] is not None:
            vf = settings["variation_frequency"]
            if not isinstance(vf, (int, float)) or vf < 0.0 or vf > 1.0:
                raise ValidationError("variation_frequency must be a number between 0.0 and 1.0")

        if "leech_threshold" in settings and settings["leech_threshold"] is not None:
            lt = settings["leech_threshold"]
            if not isinstance(lt, int) or lt < 1:
                raise ValidationError("leech_threshold must be an integer >= 1")

        if "daily_review_limit" in settings and settings["daily_review_limit"] is not None:
            drl = settings["daily_review_limit"]
            if not isinstance(drl, int) or drl < 1:
                raise ValidationError("daily_review_limit must be an integer >= 1")

        if "daily_new_limit" in settings and settings["daily_new_limit"] is not None:
            dnl = settings["daily_new_limit"]
            if not isinstance(dnl, int) or dnl < 1:
                raise ValidationError("daily_new_limit must be an integer >= 1")

        # Create deck
        deck = self.deck_repo.create(
            session,
            user_id=user_id,
            name=name.strip(),
            description=description,
            **settings,
        )

        return deck

    def get_user_decks(
        self,
        session: Session,
        user_id: uuid.UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Deck]:
        """Get all decks for a user with pagination.

        Args:
            session: SQLAlchemy session.
            user_id: ID of the user.
            skip: Number of decks to skip (default 0).
            limit: Maximum number of decks to return (default 100).

        Returns:
            List of Deck entities for the user.
        """
        return self.deck_repo.get_by_user(session, user_id, skip=skip, limit=limit)

    def get_deck(
        self,
        session: Session,
        deck_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> Deck:
        """Get a deck by ID, ensuring user owns it.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of the deck to retrieve.
            user_id: ID of the user requesting the deck.

        Returns:
            The Deck instance.

        Raises:
            DeckNotFoundError: If deck doesn't exist.
            PermissionError: If user doesn't own the deck.
        """
        try:
            deck = self.deck_repo.get(session, deck_id)
        except Exception as e:
            raise DeckNotFoundError(f"Deck with id {deck_id} not found") from e

        if deck.user_id != user_id:
            raise PermissionError("User does not own this deck")

        return deck

    def update_deck(
        self,
        session: Session,
        deck_id: uuid.UUID,
        user_id: uuid.UUID,
        **updates: Any,
    ) -> Deck:
        """Update a deck, verifying ownership.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of the deck to update.
            user_id: ID of the user requesting the update.
            **updates: Fields to update.

        Returns:
            The updated Deck instance.

        Raises:
            DeckNotFoundError: If deck doesn't exist.
            PermissionError: If user doesn't own the deck.
            ValidationError: If update data is invalid.
        """
        # Verify ownership first (raises if not found or not owned)
        self.get_deck(session, deck_id, user_id)

        # Validate any updates
        if "name" in updates and updates["name"] is not None:
            name = updates["name"]
            if not name or not isinstance(name, str) or len(name.strip()) == 0:
                raise ValidationError("Deck name is required and must not be empty")
            if len(name) > 200:
                raise ValidationError("Deck name must be at most 200 characters")
            updates["name"] = name.strip()

        if "description" in updates and updates["description"] is not None:
            description = updates["description"]
            if len(description) > 1000:
                raise ValidationError("Deck description must be at most 1000 characters")

        if "variation_frequency" in updates and updates["variation_frequency"] is not None:
            vf = updates["variation_frequency"]
            if not isinstance(vf, (int, float)) or vf < 0.0 or vf > 1.0:
                raise ValidationError("variation_frequency must be a number between 0.0 and 1.0")

        if "leech_threshold" in updates and updates["leech_threshold"] is not None:
            lt = updates["leech_threshold"]
            if not isinstance(lt, int) or lt < 1:
                raise ValidationError("leech_threshold must be an integer >= 1")

        if "daily_review_limit" in updates and updates["daily_review_limit"] is not None:
            drl = updates["daily_review_limit"]
            if not isinstance(drl, int) or drl < 1:
                raise ValidationError("daily_review_limit must be an integer >= 1")

        if "daily_new_limit" in updates and updates["daily_new_limit"] is not None:
            dnl = updates["daily_new_limit"]
            if not isinstance(dnl, int) or dnl < 1:
                raise ValidationError("daily_new_limit must be an integer >= 1")

        # Remove None values from updates
        updates = {k: v for k, v in updates.items() if v is not None}

        # Update deck
        return self.deck_repo.update(session, deck_id, **updates)

    def delete_deck(
        self,
        session: Session,
        deck_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> None:
        """Delete a deck, verifying ownership.

        Args:
            session: SQLAlchemy session.
            deck_id: ID of the deck to delete.
            user_id: ID of the user requesting deletion.

        Raises:
            DeckNotFoundError: If deck doesn't exist.
            PermissionError: If user doesn't own the deck.
        """
        # Verify ownership first (raises if not found or not owned)
        self.get_deck(session, deck_id, user_id)

        # Delete the deck
        self.deck_repo.delete(session, deck_id)
