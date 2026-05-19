"""Strategy selector for variation generation."""

from __future__ import annotations


def select_strategy(*, reps: int, lapses: int, recent_ratings: list[int]) -> str:
    """Pick rephrase | specialize | generalize based on FSRS signal.

    Rules:
      - High lapses or recent failures → rephrase (keep difficulty steady;
        defeat memorised wording).
      - Many reps with consistently high ratings → generalize (push deeper).
      - Otherwise → specialize (concrete instance to anchor learning).

    Args:
        reps: Total number of reviews for this card.
        lapses: Total number of lapses (forgotten) for this card.
        recent_ratings: List of recent review ratings (1-4 scale).

    Returns:
        One of "rephrase", "specialize", or "generalize".
    """
    recent = recent_ratings[-3:] if recent_ratings else []
    avg_recent = sum(recent) / len(recent) if recent else 3
    if lapses >= 3 or avg_recent < 2.5:
        return "rephrase"
    if reps >= 10 and avg_recent >= 3.8:
        return "generalize"
    return "specialize"
