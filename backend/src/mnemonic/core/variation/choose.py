"""Choose which stored variation (if any) to show for a card.

Pure: the caller supplies the random ``roll`` so selection is deterministic in tests.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class VariationCandidate:
    """A non-invalidated variation with its displayable text."""

    variation_id: str
    question: str
    answer: str
    shown_count: int
    generated_at: datetime


def choose_variation(
    candidates: list[VariationCandidate],
    *,
    enabled: bool,
    frequency: float,
    roll: float,
) -> VariationCandidate | None:
    """Pick a variation to display, or None to show the base card.

    Args:
        candidates: Non-invalidated variations available for this card.
        enabled: The deck's ``variation_enabled`` flag.
        frequency: The deck's ``variation_frequency`` (clamped to [0.0, 1.0]).
        roll: A random draw in [0.0, 1.0); a variation is used when ``roll < frequency``.

    Returns:
        The chosen candidate — lowest ``shown_count``, ties broken by newest
        ``generated_at`` then by ``variation_id`` — or None.
    """
    if not enabled or not candidates:
        return None
    clamped = min(1.0, max(0.0, frequency))
    if roll >= clamped:
        return None
    return min(
        candidates,
        key=lambda c: (c.shown_count, -c.generated_at.timestamp(), c.variation_id),
    )
