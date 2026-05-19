"""Review service: persists a rating, updates FSRS state, appends ReviewLog."""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from sqlalchemy import Engine

from mnemonic.core.fsrs.models import CardState
from mnemonic.core.fsrs.scheduler import schedule_review
from mnemonic.db.models import ReviewLog, SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import CardNotFoundError
from mnemonic.vault.repository import VaultRepository


def _last_review_time(session, card_id: str) -> datetime | None:
    row = (
        session.query(ReviewLog)
        .filter(ReviewLog.card_id == card_id)
        .order_by(ReviewLog.review_time.desc())
        .first()
    )
    return row.review_time if row else None


def _to_fsrs_state(row: SchedulingState, last_review: datetime | None) -> CardState:
    now = datetime.now()
    if last_review is None:
        elapsed = 0.0
    else:
        elapsed = max(0.0, (now - last_review).total_seconds() / 86400.0)
    scheduled = 0.0
    if row.due is not None and last_review is not None:
        scheduled = max(0.0, (row.due - last_review).total_seconds() / 86400.0)
    return CardState(
        stability=row.stability,
        difficulty=row.difficulty,
        elapsed_days=elapsed,
        scheduled_days=scheduled,
        reps=row.reps,
        lapses=row.lapses,
        state=row.state,
        last_review=last_review,
    )


class ReviewService:
    """Service for processing card reviews and updating FSRS state.

    Args:
        repo: VaultRepository for card lookup.
        engine: SQLAlchemy engine for the SQLite state database.
    """

    def __init__(self, *, repo: VaultRepository, engine: Engine):
        self.repo = repo
        self.engine = engine

    def rate(
        self,
        *,
        card_id: str,
        rating: int,
        response_time_ms: int,
        variation_id: str | None = None,
        variation_helpful: int | None = None,
    ) -> None:
        """Record a review rating for a card and update its FSRS state.

        Looks up the card in the vault, applies FSRS scheduling, and persists
        both the updated SchedulingState and a new ReviewLog entry atomically.

        Args:
            card_id: Unique identifier for the card (e.g. ``card-aaaabbbb``).
            rating: FSRS rating (1=Again, 2=Hard, 3=Good, 4=Easy).
            response_time_ms: Time taken to answer, in milliseconds.
            variation_id: Optional ID of the LLM variation shown (if any).
            variation_helpful: Optional user feedback on variation helpfulness.

        Raises:
            CardNotFoundError: If no card with ``card_id`` exists in the vault.
            InvalidRatingError: If ``rating`` is not in {1, 2, 3, 4}.
        """
        card = self.repo.get_card(card_id)
        if card is None:
            raise CardNotFoundError(
                f"Card '{card_id}' not found in vault. "
                "Ensure the card ID is correct and the vault is up to date."
            )

        with session_scope(self.engine) as s:
            state = s.get(SchedulingState, card_id)
            if state is None:
                state = SchedulingState(
                    card_id=card_id,
                    state="new",
                    stability=0.0,
                    difficulty=5.0,
                    reps=0,
                    lapses=0,
                    leech_score=0.0,
                )
                s.add(state)
                s.flush()

            state_before_str = state.state
            stability_before = state.stability
            difficulty_before = state.difficulty

            last_review = _last_review_time(s, card_id)
            fsrs_state = _to_fsrs_state(state, last_review)
            # InvalidRatingError propagates up if rating is out of range
            outcome = schedule_review(fsrs_state, rating)

            state.state = outcome.new_state
            state.stability = outcome.new_stability
            state.difficulty = outcome.new_difficulty
            state.reps = outcome.new_reps
            state.lapses = outcome.new_lapses
            state.due = datetime.now() + timedelta(days=outcome.new_interval)
            state.updated_at = datetime.now()

            s.add(
                ReviewLog(
                    id=uuid.uuid4().hex,
                    card_id=card_id,
                    rating=rating,
                    response_time_ms=response_time_ms,
                    review_time=datetime.now(),
                    state_before=state_before_str,
                    state_after=outcome.new_state,
                    stability_before=stability_before,
                    stability_after=outcome.new_stability,
                    difficulty_before=difficulty_before,
                    difficulty_after=outcome.new_difficulty,
                    variation_id=variation_id,
                    variation_helpful=variation_helpful,
                )
            )
