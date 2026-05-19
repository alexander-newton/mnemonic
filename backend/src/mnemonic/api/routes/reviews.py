"""Review endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from mnemonic.api.deps import get_engine, get_repo
from mnemonic.exceptions import CardNotFoundError, InvalidRatingError
from mnemonic.services.review import ReviewService

router = APIRouter(prefix="/reviews", tags=["reviews"])


class RatePayload(BaseModel):
    card_id: str
    rating: int = Field(..., ge=1, le=4)
    response_time_ms: int = Field(..., ge=0)
    variation_id: str | None = None
    variation_helpful: int | None = None


@router.post("/rate")
def rate(
    payload: RatePayload,
    repo=Depends(get_repo),
    engine=Depends(get_engine),
):
    """Record a card review rating.

    Args:
        payload: Rating payload with card ID, rating, and timing info.
        repo: Injected VaultRepository.
        engine: Injected SQLAlchemy engine.

    Returns:
        ``{"ok": True}`` on success.

    Raises:
        HTTPException 404: Card not found in vault.
        HTTPException 400: Invalid rating value.
    """
    svc = ReviewService(repo=repo, engine=engine)
    try:
        svc.rate(
            card_id=payload.card_id,
            rating=payload.rating,
            response_time_ms=payload.response_time_ms,
            variation_id=payload.variation_id,
            variation_helpful=payload.variation_helpful,
        )
    except CardNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except InvalidRatingError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"ok": True}
