"""Pick which model to use for a given strategy + FSRS context."""

from __future__ import annotations


def pick_model(
    *,
    strategy: str,
    recent_failures: int,
    model_default: str,
    model_rephrase: str,
) -> str:
    """Return the model string to use.

    Rules (per spec §6.3):
      - Strategy == "rephrase" → model_rephrase (Haiku-tier)
      - Otherwise → model_default (Sonnet-tier)
      - If recent_failures > 3 → force model_default regardless of strategy

    Args:
        strategy: Variation strategy name (e.g., "rephrase", "specialize").
        recent_failures: Number of recent failures for this card.
        model_default: Default model to use (Sonnet-tier).
        model_rephrase: Model to use for rephrase strategy (Haiku-tier).

    Returns:
        The model string to use for this request.
    """
    if recent_failures > 3:
        return model_default
    if strategy == "rephrase":
        return model_rephrase
    return model_default
