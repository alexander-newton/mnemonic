"""Tests for the calibration-surprise reward with geometric decay."""

from __future__ import annotations

import math

from mnemonic.core.optimization.reward import (
    RewardConfig,
    SubsequentReview,
    compute_reward,
)


def test_passing_an_unexpected_card_scores_positive():
    # FSRS predicted 30% recall; the user recalled it -> positive surprise.
    reviews = [SubsequentReview(success=True, predicted_retrievability=0.3)]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert math.isclose(result.reward, 0.7)
    assert result.maturity == 1
    assert result.finalized is False  # only 1 of 3 reviews landed


def test_failing_an_easy_card_scores_negative():
    reviews = [SubsequentReview(success=False, predicted_retrievability=0.9)]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert math.isclose(result.reward, -0.9)


def test_geometric_decay_weights_later_reviews_less():
    # surprises: +0.5 (w=1), then -0.5 (w=0.5). Weighted mean:
    # (1*0.5 + 0.5*-0.5) / (1 + 0.5) = 0.25 / 1.5
    reviews = [
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=False, predicted_retrievability=0.5),
    ]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert math.isclose(result.reward, 0.25 / 1.5)
    assert result.maturity == 2


def test_window_caps_at_k_and_finalizes():
    reviews = [
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=True, predicted_retrievability=0.5),
        SubsequentReview(success=True, predicted_retrievability=0.5),  # ignored
    ]
    result = compute_reward(reviews, RewardConfig(gamma=0.5, window_k=3))
    assert result.maturity == 3
    assert result.finalized is True


def test_card_retired_finalizes_even_when_immature():
    reviews = [SubsequentReview(success=True, predicted_retrievability=0.5)]
    result = compute_reward(
        reviews, RewardConfig(gamma=0.5, window_k=3), card_retired=True
    )
    assert result.maturity == 1
    assert result.finalized is True


def test_empty_reviews_returns_no_signal():
    result = compute_reward([], RewardConfig(gamma=0.5, window_k=3))
    assert result.reward is None
    assert result.maturity == 0
    assert result.finalized is False


def test_empty_reviews_with_retired_card_finalizes_with_no_reward():
    result = compute_reward([], RewardConfig(gamma=0.5, window_k=3), card_retired=True)
    assert result.reward is None
    assert result.maturity == 0
    assert result.finalized is True
