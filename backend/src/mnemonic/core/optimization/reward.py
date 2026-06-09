"""Calibration-surprise reward with geometric decay over subsequent reviews.

The reward for a variation is how much the base card's later reviews beat the
FSRS-predicted retrievability, weighted so the next review dominates and later
reviews contribute a decayed durability tail.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardConfig:
    """Parameters controlling the reward window.

    Attributes:
        gamma: Geometric decay applied to each later review (0 < gamma <= 1).
        window_k: Maximum number of subsequent reviews to consider.
    """

    gamma: float = 0.5
    window_k: int = 3


@dataclass(frozen=True)
class SubsequentReview:
    """One review that followed the shown variation.

    Attributes:
        success: True if the user recalled the card (rating >= 2).
        predicted_retrievability: FSRS R at the moment of this review (0..1).
    """

    success: bool
    predicted_retrievability: float


@dataclass(frozen=True)
class RewardResult:
    """Outcome of a reward computation.

    Attributes:
        reward: Weighted calibration surprise, or None when no usable reviews
            were available (we never fabricate a signal).
        maturity: Number of reviews that contributed (0..window_k).
        finalized: True once the window is full or the card was retired.
    """

    reward: float | None
    maturity: int
    finalized: bool


def compute_reward(
    reviews: list[SubsequentReview],
    config: RewardConfig,
    *,
    card_retired: bool = False,
) -> RewardResult:
    """Compute the maturity-weighted calibration-surprise reward.

    Args:
        reviews: Subsequent reviews of the base card, in chronological order,
            already filtered for same-session cramming. Only the first
            ``config.window_k`` are used.
        config: Reward window parameters.
        card_retired: True if the card was suspended/deleted, which finalizes
            the label even when the window is not full.

    Returns:
        A RewardResult. ``reward`` is None when there are no usable reviews.
    """
    used = reviews[: config.window_k]
    if not used:
        return RewardResult(reward=None, maturity=0, finalized=card_retired)

    numerator = 0.0
    denominator = 0.0
    for index, review in enumerate(used):
        weight = config.gamma**index
        surprise = (1.0 if review.success else 0.0) - review.predicted_retrievability
        numerator += weight * surprise
        denominator += weight

    reward = numerator / denominator
    maturity = len(used)
    finalized = maturity >= config.window_k or card_retired
    return RewardResult(reward=reward, maturity=maturity, finalized=finalized)
