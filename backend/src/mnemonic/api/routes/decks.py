"""Deck endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mnemonic.api.deps import get_deck_service
from mnemonic.services.deck import DeckService

router = APIRouter(prefix="/decks", tags=["decks"])


@router.get("")
def list_decks(svc: DeckService = Depends(get_deck_service)):
    return [
        {
            "folder_name": d.folder.name,
            "name": d.name,
            "config": d.config.__dict__ if d.config else None,
        }
        for d in svc.list()
    ]


@router.get("/{folder_name}")
def get_deck(folder_name: str, svc: DeckService = Depends(get_deck_service)):
    d = svc.get(folder_name)
    if d is None:
        raise HTTPException(status_code=404, detail=f"Deck '{folder_name}' not found.")
    return {
        "folder_name": d.folder.name,
        "name": d.name,
        "config": d.config.__dict__ if d.config else None,
    }
