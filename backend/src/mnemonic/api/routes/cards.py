"""Card API endpoints for CRUD operations.

Provides endpoints for:
- GET /decks/{deck_id}/cards - List cards in a deck
- POST /decks/{deck_id}/cards - Create new card
- GET /cards/{card_id} - Get specific card
- PUT /cards/{card_id} - Update card
- DELETE /cards/{card_id} - Delete card
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from mnemonic.api.deps import get_current_user, get_db
from mnemonic.api.models.card import (
    CardResponse,
    CreateCardRequest,
    UpdateCardRequest,
)
from mnemonic.db.models.user import User
from mnemonic.db.repositories.card import CardRepository
from mnemonic.db.repositories.deck import DeckRepository
from mnemonic.exceptions import CardNotFoundError, DeckNotFoundError, ValidationError
from mnemonic.services.card import CardService

router = APIRouter(tags=["cards"])


def get_card_service(_session: Session = Depends(get_db)) -> CardService:
    """Get CardService instance with injected dependencies.

    Args:
        _session: Database session (unused, but required for dependency injection).

    Returns:
        CardService instance.
    """
    card_repo = CardRepository()
    deck_repo = DeckRepository()
    return CardService(card_repo, deck_repo)


@router.get("/decks/{deck_id}/cards", response_model=list[CardResponse])
async def list_cards(
    deck_id: uuid.UUID,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    card_service: CardService = Depends(get_card_service),
) -> list[CardResponse]:
    """List all cards in a deck.

    Supports pagination with skip and limit parameters.

    Args:
        deck_id: ID of the deck to get cards from.
        skip: Number of cards to skip (default 0, min 0).
        limit: Maximum cards to return (default 100, max 100).
        current_user: Current authenticated user.
        session: Database session.
        card_service: Card service instance.

    Returns:
        List of CardResponse objects in the deck.

    Raises:
        401: If user is not authenticated.
        403: If user doesn't own the deck.
        404: If deck doesn't exist.
    """
    try:
        cards = card_service.get_deck_cards(
            session, current_user.id, deck_id, skip=skip, limit=limit
        )
        return [CardResponse.model_validate(card) for card in cards]
    except DeckNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.post("/decks/{deck_id}/cards", response_model=CardResponse, status_code=201)
async def create_card(
    deck_id: uuid.UUID,
    data: CreateCardRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    card_service: CardService = Depends(get_card_service),
) -> CardResponse:
    """Create a new card in a deck.

    Args:
        deck_id: ID of the deck to create the card in.
        data: CreateCardRequest with card content and configuration.
        current_user: Current authenticated user.
        session: Database session.
        card_service: Card service instance.

    Returns:
        CardResponse with created card details.

    Raises:
        400: If card configuration is invalid.
        401: If user is not authenticated.
        403: If user doesn't own the deck.
        404: If deck or card_type doesn't exist.
        422: If request data format is invalid.
    """
    try:
        card = card_service.create_card(
            session,
            current_user.id,
            deck_id,
            content=data.content,
            card_type_id=data.card_type_id,
            notes=data.notes,
            tags=data.tags,
        )
        return CardResponse.model_validate(card)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except DeckNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.get("/cards/{card_id}", response_model=CardResponse)
async def get_card(
    card_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    card_service: CardService = Depends(get_card_service),
) -> CardResponse:
    """Get a specific card by ID.

    User must own the card's deck to retrieve it.

    Args:
        card_id: ID of the card to retrieve.
        current_user: Current authenticated user.
        session: Database session.
        card_service: Card service instance.

    Returns:
        CardResponse with card details.

    Raises:
        401: If user is not authenticated.
        403: If user doesn't own the card's deck.
        404: If card doesn't exist.
    """
    try:
        card = card_service.get_card(session, card_id, current_user.id)
        return CardResponse.model_validate(card)
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.put("/cards/{card_id}", response_model=CardResponse)
async def update_card(
    card_id: uuid.UUID,
    data: UpdateCardRequest,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    card_service: CardService = Depends(get_card_service),
) -> CardResponse:
    """Update a card.

    User must own the card's deck to update it. Only provided fields are updated.

    Args:
        card_id: ID of the card to update.
        data: UpdateCardRequest with fields to update.
        current_user: Current authenticated user.
        session: Database session.
        card_service: Card service instance.

    Returns:
        CardResponse with updated card details.

    Raises:
        400: If update data is invalid.
        401: If user is not authenticated.
        403: If user doesn't own the card's deck.
        404: If card doesn't exist.
        422: If request data format is invalid.
    """
    try:
        # Build update dict with only provided fields
        updates = {}
        if data.content is not None:
            updates["content"] = data.content
        if data.notes is not None:
            updates["notes"] = data.notes
        if data.tags is not None:
            updates["tags"] = data.tags
        if data.suspended is not None:
            updates["suspended"] = data.suspended

        card = card_service.update_card(session, card_id, current_user.id, **updates)
        return CardResponse.model_validate(card)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=str(e)) from e
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e


@router.delete("/cards/{card_id}", status_code=204)
async def delete_card(
    card_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    session: Session = Depends(get_db),
    card_service: CardService = Depends(get_card_service),
) -> None:
    """Delete a card.

    User must own the card's deck to delete it.

    Args:
        card_id: ID of the card to delete.
        current_user: Current authenticated user.
        session: Database session.
        card_service: Card service instance.

    Raises:
        401: If user is not authenticated.
        403: If user doesn't own the card's deck.
        404: If card doesn't exist.
    """
    try:
        card_service.delete_card(session, card_id, current_user.id)
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e)) from e
