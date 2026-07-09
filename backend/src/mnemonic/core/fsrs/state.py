"""Build an FSRS CardState from stored scheduling fields plus the last review time."""

from __future__ import annotations

from datetime import datetime

from mnemonic.core.fsrs.models import CardState


def to_card_state(
    *,
    stability: float,
    difficulty: float,
    reps: int,
    lapses: int,
    state: str,
    due: datetime | None,
    last_review: datetime | None,
    now: datetime,
) -> CardState:
    """Construct a CardState, deriving elapsed/scheduled days from the last review.

    Args:
        stability, difficulty, reps, lapses, state: Stored FSRS fields.
        due: The card's current due date (or None for a new card).
        last_review: Timestamp of the last review (or None).
        now: Current time, used to compute elapsed days.

    Returns:
        A CardState suitable for schedule_review / preview_schedule.
    """
    if last_review is None:
        elapsed = 0.0
    else:
        elapsed = max(0.0, (now - last_review).total_seconds() / 86400.0)
    scheduled = 0.0
    if due is not None and last_review is not None:
        scheduled = max(0.0, (due - last_review).total_seconds() / 86400.0)
    return CardState(
        stability=stability,
        difficulty=difficulty,
        elapsed_days=elapsed,
        scheduled_days=scheduled,
        reps=reps,
        lapses=lapses,
        state=state,
        last_review=last_review,
    )
