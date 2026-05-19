"""FSRS scheduler data structures.

This module defines the data structures for the FSRS scheduler:
- CardState: Current memory state of a card
- ReviewOutcome: Result of scheduling a review
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass
class CardState:
    """Current memory state of a card for FSRS scheduling.

    This represents the complete state needed to schedule a review
    using the FSRS (Free Spaced Repetition Scheduler) algorithm.

    Attributes:
        stability: Memory stability in days. How long until retrievability
            decays to the target retention rate. Starts at 0 for new cards.
        difficulty: Card difficulty on a 1-10 scale, where:
            - 1 = very easy
            - 5 = medium
            - 10 = very hard
        elapsed_days: Days since the last review. For new cards, this is 0.
            Must be non-negative.
        scheduled_days: Days until the next scheduled review (before this review).
        reps: Number of times this card has been successfully reviewed.
        lapses: Number of times this card has failed (rating=1).
        state: Learning state of the card - one of:
            - "new": Not yet reviewed
            - "learning": Being learned, not in long-term review cycle
            - "review": In regular review cycle
            - "relearning": Failed card being relearned
        last_review: Timestamp of the last review. None for new cards.
    """

    stability: float
    difficulty: float
    elapsed_days: float
    scheduled_days: float
    reps: int
    lapses: int
    state: str
    last_review: datetime | None


@dataclass
class ReviewOutcome:
    """Result of scheduling a review.

    This represents the new state of the card after applying FSRS
    calculations for a specific rating.

    Attributes:
        new_stability: Updated memory stability (days).
        new_difficulty: Updated card difficulty (1-10 scale).
        new_interval: Days until next review (the scheduling interval).
        new_state: Updated learning state (new/learning/review/relearning).
        new_reps: Updated successful review count.
        new_lapses: Updated failure count.
    """

    new_stability: float
    new_difficulty: float
    new_interval: int
    new_state: str
    new_reps: int
    new_lapses: int
