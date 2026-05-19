"""Deck API endpoints for CRUD operations.

Provides endpoints for:
- GET /decks - List user's decks
- POST /decks - Create new deck
- GET /decks/{deck_id} - Get specific deck
- PUT /decks/{deck_id} - Update deck
- DELETE /decks/{deck_id} - Delete deck
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from mnemonic.api.deps import get_current_user, get_db
from mnemonic.api.models.deck import (
    CreateDeckRequest,
    DeckResponse,
    UpdateDeckRequest,
)
from mnemonic.db.models.user import User
from mnemonic.db.repositories.deck import DeckRepository
from mnemonic.exceptions import DeckNotFoundError, ValidationError
from mnemonic.services.deck import DeckService

router = APIRouter(prefix="/decks", tags=["decks"])


def get_deck_service(_session: Session = Depends(get_db)) -> DeckService:
    """Get DeckService instance with injected dependencies.

    Args:
        _session: Database session (unused, but required for dependency injection).

    Returns:
        DeckService instance.
    """
    deck_repo = DeckRepository()
    return DeckService(deck_repo)


@router.get("", response_model=list[DeckResponse])
async def list_decks(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    deck_service: DeckService = Depends(get_deck_service),
) -> list[DeckResponse]:
    """List all decks for the authenticated user.

    Supports pagination with skip and limit parameters.

    Args:
        skip: Number of decks to skip (default 0, min 0).
        limit: Maximum decks to return (default 100, max 100).
        current_user: Current authenticated user.
        session: Database session.
        deck_service: Deck service instance.

    Returns:
        List of DeckResponse objects for the user's decks.

    Raises:
        401: If user is not authenticated.
    """
    decks = deck_service.get_user_decks(session, current_user.id, skip=skip, limit=limit)
    return [DeckResponse.model_validate(deck) for deck in decks]


@router.post("", response_model=DeckResponse, status_code=201)
async def create_deck(
    data: CreateDeckRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    deck_service: DeckService = Depends(get_deck_service),
) -> DeckResponse:
    """Create a new deck for the authenticated user.

    Args:
        data: CreateDeckRequest with deck configuration.
        current_user: Current authenticated user.
        session: Database session.
        deck_service: Deck service instance.

    Returns:
        DeckResponse with created deck details.

    Raises:
        400: If deck configuration is invalid.
        401: If user is not authenticated.
        422: If request data format is invalid.
    """
    try:
        deck = deck_service.create_deck(
            session,
            current_user.id,
            name=data.name,
            description=data.description,
            variation_enabled=data.variation_enabled,
            variation_frequency=data.variation_frequency,
            leech_threshold=data.leech_threshold,
            daily_review_limit=data.daily_review_limit,
            daily_new_limit=data.daily_new_limit,
        )
        return DeckResponse.model_validate(deck)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e


@router.get("/{deck_id}", response_model=DeckResponse)
async def get_deck(
    deck_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    deck_service: DeckService = Depends(get_deck_service),
) -> DeckResponse:
    """Get a specific deck by ID.

    User must own the deck to retrieve it.

    Args:
        deck_id: ID of the deck to retrieve.
        current_user: Current authenticated user.
        session: Database session.
        deck_service: Deck service instance.

    Returns:
        DeckResponse with deck details.

    Raises:
        401: If user is not authenticated.
        403: If user doesn't own the deck.
        404: If deck doesn't exist.
    """
    try:
        deck = deck_service.get_deck(session, deck_id, current_user.id)
        return DeckResponse.model_validate(deck)
    except DeckNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.put("/{deck_id}", response_model=DeckResponse)
async def update_deck(
    deck_id: uuid.UUID,
    data: UpdateDeckRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    deck_service: DeckService = Depends(get_deck_service),
) -> DeckResponse:
    """Update a deck.

    User must own the deck to update it. Only provided fields are updated.

    Args:
        deck_id: ID of the deck to update.
        data: UpdateDeckRequest with fields to update.
        current_user: Current authenticated user.
        session: Database session.
        deck_service: Deck service instance.

    Returns:
        DeckResponse with updated deck details.

    Raises:
        400: If update data is invalid.
        401: If user is not authenticated.
        403: If user doesn't own the deck.
        404: If deck doesn't exist.
        422: If request data format is invalid.
    """
    try:
        # Build update dict with only provided fields
        updates = {}
        if data.name is not None:
            updates["name"] = data.name
        if data.description is not None:
            updates["description"] = data.description
        if data.variation_enabled is not None:
            updates["variation_enabled"] = data.variation_enabled
        if data.variation_frequency is not None:
            updates["variation_frequency"] = data.variation_frequency
        if data.leech_threshold is not None:
            updates["leech_threshold"] = data.leech_threshold
        if data.daily_review_limit is not None:
            updates["daily_review_limit"] = data.daily_review_limit
        if data.daily_new_limit is not None:
            updates["daily_new_limit"] = data.daily_new_limit

        deck = deck_service.update_deck(session, deck_id, current_user.id, **updates)
        return DeckResponse.model_validate(deck)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DeckNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.delete("/{deck_id}", status_code=204)
async def delete_deck(
    deck_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    deck_service: DeckService = Depends(get_deck_service),
) -> None:
    """Delete a deck.

    User must own the deck to delete it. Also deletes all cards in the deck.

    Args:
        deck_id: ID of the deck to delete.
        current_user: Current authenticated user.
        session: Database session.
        deck_service: Deck service instance.

    Raises:
        401: If user is not authenticated.
        403: If user doesn't own the deck.
        404: If deck doesn't exist.
    """
    try:
        deck_service.delete_deck(session, deck_id, current_user.id)
    except DeckNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
