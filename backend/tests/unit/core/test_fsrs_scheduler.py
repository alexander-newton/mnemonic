"""Tests for FSRS scheduler - calculates new card state after review.

This module tests the scheduler logic that takes a card's current FSRS state
and a rating (1-4), then returns the new state after applying FSRS formulas.

All tests are written BEFORE implementation (TDD), defining expected behavior.

Key concepts:
- Rating 1 (Again): Failed recall, needs relearning
- Rating 2 (Hard): Difficult but correct recall
- Rating 3 (Good): Successful recall
- Rating 4 (Easy): Very easy recall
"""

import math
from datetime import datetime

import pytest

from mnemonic.core.fsrs.models import CardState, ReviewOutcome
from mnemonic.core.fsrs.parameters import FSRSParameters
from mnemonic.core.fsrs.scheduler import (
    calculate_next_difficulty,
    calculate_next_interval,
    calculate_next_stability,
    schedule_review,
)
from mnemonic.exceptions import InvalidRatingError


class TestScheduleReviewBasics:
    """Test basic schedule_review functionality."""

    def test_schedule_review_returns_review_outcome(self):
        """schedule_review should return ReviewOutcome object."""
        state = CardState(
            stability=0.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
            state="new",
            last_review=None,
        )
        outcome = schedule_review(state, rating=3)
        assert isinstance(outcome, ReviewOutcome)

    def test_schedule_review_with_default_parameters(self):
        """schedule_review should work without explicit parameters."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=1,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=3)
        assert isinstance(outcome, ReviewOutcome)


class TestNewCardScheduling:
    """Test scheduling for new cards (state="new")."""

    def test_new_card_with_again_enters_learning(self):
        """New card failed (rating=1) should enter learning state."""
        state = CardState(
            stability=0.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
            state="new",
            last_review=None,
        )
        outcome = schedule_review(state, rating=1)
        assert outcome.new_state == "learning"
        assert outcome.new_lapses == 1  # Failed counts as a lapse
        assert outcome.new_reps == 0  # No successful rep yet

    def test_new_card_with_hard_enters_learning(self):
        """New card with hard (rating=2) should enter learning state."""
        state = CardState(
            stability=0.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
            state="new",
            last_review=None,
        )
        outcome = schedule_review(state, rating=2)
        assert outcome.new_state == "learning"
        assert outcome.new_reps == 1  # Hard is still a successful rep

    def test_new_card_with_good_enters_review(self):
        """New card with good (rating=3) should enter review state."""
        state = CardState(
            stability=0.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
            state="new",
            last_review=None,
        )
        outcome = schedule_review(state, rating=3)
        assert outcome.new_state == "review"
        assert outcome.new_reps == 1  # First successful rep
        assert outcome.new_lapses == 0
        assert outcome.new_interval > 0

    def test_new_card_with_easy_enters_review(self):
        """New card with easy (rating=4) should enter review state."""
        state = CardState(
            stability=0.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
            state="new",
            last_review=None,
        )
        outcome = schedule_review(state, rating=4)
        assert outcome.new_state == "review"
        assert outcome.new_reps == 1
        assert outcome.new_interval > 0


class TestLearningCardScheduling:
    """Test scheduling for learning cards (state="learning")."""

    def test_learning_card_with_again_stays_learning(self):
        """Learning card failed (rating=1) should stay in learning."""
        state = CardState(
            stability=0.5,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=1.0,
            reps=0,
            lapses=1,
            state="learning",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=1)
        assert outcome.new_state == "learning"
        assert outcome.new_lapses == 2  # Increment lapse count

    def test_learning_card_with_good_enters_review(self):
        """Learning card with good (rating=3) should enter review."""
        state = CardState(
            stability=0.5,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=1.0,
            reps=0,
            lapses=1,
            state="learning",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=3)
        assert outcome.new_state == "review"
        assert outcome.new_reps == 1


class TestReviewCardScheduling:
    """Test scheduling for review cards (state="review")."""

    def test_review_card_with_again_enters_relearning(self):
        """Review card failed (rating=1) should enter relearning."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=3,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=1)
        assert outcome.new_state == "relearning"
        assert outcome.new_lapses == 1

    def test_review_card_with_hard_stays_review(self):
        """Review card with hard (rating=2) should stay in review."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=3,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=2)
        assert outcome.new_state == "review"
        assert outcome.new_reps == 4
        assert outcome.new_lapses == 0

    def test_review_card_with_good_stays_review(self):
        """Review card with good (rating=3) should stay in review."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=3,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=3)
        assert outcome.new_state == "review"
        assert outcome.new_reps == 4

    def test_review_card_with_easy_stays_review(self):
        """Review card with easy (rating=4) should stay in review."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=3,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=4)
        assert outcome.new_state == "review"
        assert outcome.new_reps == 4


class TestRelearningCardScheduling:
    """Test scheduling for relearning cards (state="relearning")."""

    def test_relearning_card_with_again_stays_relearning(self):
        """Relearning card failed (rating=1) should stay in relearning."""
        state = CardState(
            stability=5.0,
            difficulty=6.0,
            elapsed_days=0.0,
            scheduled_days=1.0,
            reps=3,
            lapses=1,
            state="relearning",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=1)
        assert outcome.new_state == "relearning"
        assert outcome.new_lapses == 2

    def test_relearning_card_with_good_enters_review(self):
        """Relearning card with good (rating=3) should enter review."""
        state = CardState(
            stability=5.0,
            difficulty=6.0,
            elapsed_days=0.0,
            scheduled_days=1.0,
            reps=3,
            lapses=1,
            state="relearning",
            last_review=datetime.now(),
        )
        outcome = schedule_review(state, rating=3)
        assert outcome.new_state == "review"


class TestRatingImpactOnStability:
    """Test that ratings affect stability correctly."""

    def test_higher_ratings_increase_stability_more(self):
        """Higher ratings should result in greater stability increases."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome_hard = schedule_review(state, rating=2)
        outcome_good = schedule_review(state, rating=3)
        outcome_easy = schedule_review(state, rating=4)

        # Rating 4 (easy) should increase stability most
        # Rating 3 (good) should increase stability moderately
        # Rating 2 (hard) should increase stability least
        # The differences are small but should be monotonic
        assert outcome_hard.new_stability < outcome_easy.new_stability
        assert outcome_good.new_stability > outcome_hard.new_stability

    def test_failed_review_decreases_stability(self):
        """Failed review (rating=1) should decrease stability."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=1)
        # Stability should be significantly reduced on failure
        assert outcome.new_stability < state.stability


class TestRatingImpactOnDifficulty:
    """Test that ratings affect difficulty correctly."""

    def test_hard_rating_increases_difficulty(self):
        """Hard rating (rating=2) should increase difficulty."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=2)
        assert outcome.new_difficulty > state.difficulty

    def test_easy_rating_decreases_difficulty(self):
        """Easy rating (rating=4) should decrease difficulty."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=4)
        assert outcome.new_difficulty < state.difficulty

    def test_good_rating_minimal_difficulty_change(self):
        """Good rating (rating=3) should have minimal difficulty change."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=3)
        # Good rating should keep difficulty relatively stable
        assert abs(outcome.new_difficulty - state.difficulty) < 1.0

    def test_difficulty_stays_in_range(self):
        """Difficulty should always be between 1 and 10."""
        state_low = CardState(
            stability=10.0,
            difficulty=1.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        state_high = CardState(
            stability=10.0,
            difficulty=10.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        # Try to increase difficulty below 1
        outcome_low = schedule_review(state_low, rating=4)  # Easy should decrease
        assert 1.0 <= outcome_low.new_difficulty <= 10.0

        # Try to increase difficulty above 10
        outcome_high = schedule_review(state_high, rating=2)  # Hard should increase
        assert 1.0 <= outcome_high.new_difficulty <= 10.0


class TestRatingImpactOnInterval:
    """Test that ratings affect review intervals correctly."""

    def test_higher_ratings_longer_intervals(self):
        """Higher ratings should schedule longer review intervals."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome_hard = schedule_review(state, rating=2)
        outcome_good = schedule_review(state, rating=3)
        outcome_easy = schedule_review(state, rating=4)

        # Intervals should tend to increase with rating
        # (May be equal due to rounding, but hard should not exceed easy)
        assert outcome_hard.new_interval <= outcome_easy.new_interval
        assert outcome_hard.new_stability < outcome_easy.new_stability

    def test_interval_increases_with_successful_reviews(self):
        """Repeated successful reviews should increase intervals."""
        state1 = CardState(
            stability=5.0,
            difficulty=5.0,
            elapsed_days=2.0,
            scheduled_days=5.0,
            reps=1,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome1 = schedule_review(state1, rating=3)

        # Simulate another review with the new stability
        state2 = CardState(
            stability=outcome1.new_stability,
            difficulty=outcome1.new_difficulty,
            elapsed_days=outcome1.new_interval,
            scheduled_days=outcome1.new_interval,
            reps=outcome1.new_reps,
            lapses=outcome1.new_lapses,
            state=outcome1.new_state,
            last_review=datetime.now(),
        )

        outcome2 = schedule_review(state2, rating=3)

        # Second interval should be longer than first
        assert outcome2.new_interval > outcome1.new_interval


class TestRepeatAndLapseCounters:
    """Test that rep and lapse counters update correctly."""

    def test_reps_incremented_on_successful_reviews(self):
        """Reps should increment only on successful reviews (rating >= 3)."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        # Rating 2 (hard) should increment reps
        outcome_hard = schedule_review(state, rating=2)
        assert outcome_hard.new_reps == state.reps + 1

        # Rating 3 (good) should increment reps
        outcome_good = schedule_review(state, rating=3)
        assert outcome_good.new_reps == state.reps + 1

        # Rating 4 (easy) should increment reps
        outcome_easy = schedule_review(state, rating=4)
        assert outcome_easy.new_reps == state.reps + 1

    def test_reps_not_incremented_on_failure(self):
        """Reps should not increment on failure (rating=1)."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=1)
        assert outcome.new_reps == state.reps  # No increment

    def test_lapses_incremented_on_failure(self):
        """Lapses should increment only on failure (rating=1)."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=1)
        assert outcome.new_lapses == state.lapses + 1

    def test_lapses_not_incremented_on_success(self):
        """Lapses should not increment on successful reviews (rating >= 2)."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        for rating in [2, 3, 4]:
            outcome = schedule_review(state, rating=rating)
            assert outcome.new_lapses == state.lapses


class TestInvalidRatings:
    """Test error handling for invalid ratings."""

    def test_raises_invalid_rating_error_for_zero(self):
        """Should raise InvalidRatingError for rating=0."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        with pytest.raises(InvalidRatingError):
            schedule_review(state, rating=0)

    def test_raises_invalid_rating_error_for_five(self):
        """Should raise InvalidRatingError for rating=5."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        with pytest.raises(InvalidRatingError):
            schedule_review(state, rating=5)

    def test_raises_invalid_rating_error_for_negative(self):
        """Should raise InvalidRatingError for negative rating."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        with pytest.raises(InvalidRatingError):
            schedule_review(state, rating=-1)

    def test_error_message_is_informative(self):
        """InvalidRatingError message should explain the problem."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        with pytest.raises(InvalidRatingError) as exc_info:
            schedule_review(state, rating=5)

        error_msg = str(exc_info.value).lower()
        assert "rating" in error_msg or "1-4" in error_msg


class TestMaximumInterval:
    """Test that maximum_interval is respected."""

    def test_interval_respects_maximum(self):
        """Interval should not exceed maximum_interval from parameters."""
        params = FSRSParameters.default()

        state = CardState(
            stability=100000.0,  # Very high stability
            difficulty=1.0,  # Very easy
            elapsed_days=10.0,
            scheduled_days=10.0,
            reps=100,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=4, parameters=params)
        assert outcome.new_interval <= params.maximum_interval


class TestCalculateNextStability:
    """Test calculate_next_stability helper function."""

    def test_new_card_stability_calculation(self):
        """New card (stability=0) should get initial stability from weights."""
        params = FSRSParameters.default()

        # For new card with rating=3 (good), use w[2]
        stability = calculate_next_stability(
            current_stability=0.0,
            current_difficulty=5.0,
            retrievability=1.0,  # Just reviewed
            rating=3,
            parameters=params,
        )

        # Should be exactly w[2] for new cards
        assert stability == params.w[2]

    def test_stability_increases_on_successful_review(self):
        """Stability should increase on successful reviews (rating >= 2)."""
        params = FSRSParameters.default()

        current_stability = 10.0

        stability = calculate_next_stability(
            current_stability=current_stability,
            current_difficulty=5.0,
            retrievability=0.9,
            rating=3,
            parameters=params,
        )

        assert stability > current_stability

    def test_stability_decreases_on_failed_review(self):
        """Stability should decrease significantly on failure (rating=1)."""
        params = FSRSParameters.default()

        current_stability = 10.0

        stability = calculate_next_stability(
            current_stability=current_stability,
            current_difficulty=5.0,
            retrievability=0.5,
            rating=1,
            parameters=params,
        )

        assert stability < current_stability


class TestCalculateNextDifficulty:
    """Test calculate_next_difficulty helper function."""

    def test_difficulty_update_for_each_rating(self):
        """Difficulty should adjust based on rating."""
        params = FSRSParameters.default()

        current_difficulty = 5.0

        d_hard = calculate_next_difficulty(current_difficulty, rating=2, parameters=params)
        d_good = calculate_next_difficulty(current_difficulty, rating=3, parameters=params)
        d_easy = calculate_next_difficulty(current_difficulty, rating=4, parameters=params)

        # Hard should increase, easy should decrease, good should be close
        assert d_hard > current_difficulty
        assert d_good <= current_difficulty + 0.5  # Minimal change
        assert d_easy < current_difficulty

    def test_difficulty_always_in_range(self):
        """Difficulty should always be clamped to [1, 10]."""
        params = FSRSParameters.default()

        # Test from minimum difficulty
        d_from_min = calculate_next_difficulty(1.0, rating=2, parameters=params)
        assert 1.0 <= d_from_min <= 10.0

        # Test from maximum difficulty
        d_from_max = calculate_next_difficulty(10.0, rating=4, parameters=params)
        assert 1.0 <= d_from_max <= 10.0


class TestCalculateNextInterval:
    """Test calculate_next_interval helper function."""

    def test_interval_positive_and_integer(self):
        """Interval should be a positive integer (days)."""
        params = FSRSParameters.default()

        interval = calculate_next_interval(stability=10.0, parameters=params)

        assert isinstance(interval, int)
        assert interval > 0

    def test_higher_stability_longer_interval(self):
        """Higher stability should result in longer intervals."""
        params = FSRSParameters.default()

        interval_low = calculate_next_interval(stability=5.0, parameters=params)
        interval_high = calculate_next_interval(stability=20.0, parameters=params)

        assert interval_high > interval_low

    def test_interval_respects_maximum(self):
        """Interval should not exceed maximum_interval."""
        params = FSRSParameters.default()

        interval = calculate_next_interval(stability=1000000.0, parameters=params)

        assert interval <= params.maximum_interval


class TestCustomParameters:
    """Test scheduling with custom parameters."""

    def test_accepts_custom_parameters(self):
        """schedule_review should accept custom FSRSParameters."""
        custom_params = FSRSParameters(
            w=[0.5] * 19,
            request_retention=0.85,
            maximum_interval=10000,
        )

        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=3, parameters=custom_params)
        assert isinstance(outcome, ReviewOutcome)
        assert outcome.new_interval <= custom_params.maximum_interval


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_zero_stability_handled(self):
        """Should handle zero stability (new card)."""
        state = CardState(
            stability=0.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=0.0,
            reps=0,
            lapses=0,
            state="new",
            last_review=None,
        )

        outcome = schedule_review(state, rating=3)
        assert outcome.new_stability > 0.0

    def test_zero_elapsed_days_handled(self):
        """Should handle zero elapsed_days (immediate review)."""
        state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=0.0,
            scheduled_days=10.0,
            reps=2,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=3)
        assert isinstance(outcome, ReviewOutcome)

    def test_very_high_stability_handled(self):
        """Should handle very high stability values."""
        state = CardState(
            stability=1000000.0,
            difficulty=1.0,
            elapsed_days=500000.0,
            scheduled_days=1000000.0,
            reps=500,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=4)
        assert isinstance(outcome, ReviewOutcome)
        assert outcome.new_interval > 0

    def test_high_rep_count_handled(self):
        """Should handle high rep counts."""
        state = CardState(
            stability=100.0,
            difficulty=5.0,
            elapsed_days=50.0,
            scheduled_days=100.0,
            reps=1000,
            lapses=5,
            state="review",
            last_review=datetime.now(),
        )

        outcome = schedule_review(state, rating=3)
        assert outcome.new_reps == 1001
        assert outcome.new_lapses == 5
