"""Single source of truth for a brand-new card's FSRS state."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class NewCardDefaults:
    """The FSRS field values of a freshly created (never-reviewed) card."""

    state: str = "new"
    stability: float = 0.0
    difficulty: float = 5.0
    due: datetime | None = None
    reps: int = 0
    lapses: int = 0


NEW_CARD_DEFAULTS = NewCardDefaults()
