"""Card endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from mnemonic.api.deps import get_card_service
from mnemonic.services.card import CardService

router = APIRouter(prefix="/cards", tags=["cards"])


def _serialize(card) -> dict:
    return {
        "card_id": card.card_id,
        "note_path": str(card.note_path),
        "deck_folder": card.deck_folder.name,
        "syntax": card.syntax,
        "front": card.front,
        "back": card.back,
        "title": card.title,
        "state": card.state,
        "stability": card.stability,
        "difficulty": card.difficulty,
        "due": card.due.isoformat() if card.due else None,
        "reps": card.reps,
        "lapses": card.lapses,
        "leech_score": card.leech_score,
        "suspended": card.suspended,
    }


@router.get("")
def list_cards(deck: str | None = Query(None), svc: CardService = Depends(get_card_service)):
    return [_serialize(c) for c in svc.list(deck_folder_name=deck)]


@router.get("/{card_id}")
def get_card(card_id: str, svc: CardService = Depends(get_card_service)):
    c = svc.get(card_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found.")
    return _serialize(c)
