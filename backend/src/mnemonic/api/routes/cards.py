"""Card endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from mnemonic.api.deps import get_card_service, get_core_change_service
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.services.card import CardService
from mnemonic.services.core_change import ChangedCard, CoreChangeService, SchedulingSnapshot

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
        "core_changed": card.core_changed,
        "core_changed_at": card.core_changed_at.isoformat() if card.core_changed_at else None,
    }


def _serialize_changed(c: ChangedCard) -> dict:
    return {
        "card_id": c.card_id,
        "title": c.title,
        "front": c.front,
        "syntax": c.syntax,
        "change_kind": c.change_kind,
        "core_changed_at": c.core_changed_at.isoformat() if c.core_changed_at else None,
        "state": c.state,
        "due": c.due.isoformat() if c.due else None,
        "stability": c.stability,
        "difficulty": c.difficulty,
    }


def _serialize_snapshot(s: SchedulingSnapshot) -> dict:
    return {
        "card_id": s.card_id,
        "core_changed": s.core_changed,
        "state": s.state,
        "stability": s.stability,
        "difficulty": s.difficulty,
        "due": s.due.isoformat() if s.due else None,
        "reps": s.reps,
        "lapses": s.lapses,
    }


class CoreChangePayload(BaseModel):
    decision: Literal["keep", "soft_reset", "full_reset"]


@router.get("")
def list_cards(deck: str | None = Query(None), svc: CardService = Depends(get_card_service)):
    return [_serialize(c) for c in svc.list(deck_folder_name=deck)]


@router.get("/changed")
def list_changed_cards(
    svc: CoreChangeService = Depends(get_core_change_service),
) -> list[dict]:
    """List cards whose core content changed since their scheduling was set."""
    return [_serialize_changed(c) for c in svc.list_changed()]


@router.post("/{card_id}/core-change")
def apply_core_change(
    card_id: str,
    payload: CoreChangePayload,
    svc: CoreChangeService = Depends(get_core_change_service),
) -> dict:
    """Apply keep / soft-reset / full-reset to a flagged card's scheduling."""
    try:
        snapshot = svc.apply(card_id=card_id, decision=payload.decision, now=datetime.now())
    except CardNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValidationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _serialize_snapshot(snapshot)


@router.get("/{card_id}")
def get_card(card_id: str, svc: CardService = Depends(get_card_service)):
    c = svc.get(card_id)
    if c is None:
        raise HTTPException(status_code=404, detail=f"Card '{card_id}' not found.")
    return _serialize(c)
