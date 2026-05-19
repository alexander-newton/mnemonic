"""Tests for FSRS preview function that shows outcomes for all ratings.

This module tests the preview_schedule() function that allows users to see
what will happen if they choose each of the four ratings before committing
to a review.

All tests are written BEFORE implementation (TDD), defining expected behavior.

Key concepts:
- Preview shows outcomes for all 4 ratings without modifying state
- Results should match what schedule_review() would produce
- Preview includes human-readable rating names
- Preview helps users make informed decisions
"""

from datetime import datetime

from mnemonic.core.fsrs.models import CardState
from mnemonic.core.fsrs.parameters import FSRSParameters
from mnemonic.core.fsrs.preview import PreviewOption, preview_schedule
from mnemonic.core.fsrs.scheduler import schedule_review


class TestPreviewScheduleBasics:
    """Test basic preview_schedule functionality."""

    def test_returns_dict(self):
        """preview_schedule should return a dictionary."""
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
        previews = preview_schedule(state)
        assert isinstance(previews, dict)

    def test_returns_four_options(self):
        """Preview should return options for all four ratings."""
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
        previews = preview_schedule(state)

        assert len(previews) == 4
        assert 1 in previews
        assert 2 in previews
        assert 3 in previews
        assert 4 in previews

    def test_returns_preview_options(self):
        """Each preview should be a PreviewOption instance."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert isinstance(previews[rating], PreviewOption)


class TestPreviewOptionStructure:
    """Test PreviewOption data structure."""

    def test_preview_option_has_rating(self):
        """PreviewOption should have rating attribute."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert previews[rating].rating == rating

    def test_preview_option_has_rating_names(self):
        """Each option should have a human-readable rating name."""
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
        previews = preview_schedule(state)

        assert previews[1].rating_name == "Again"
        assert previews[2].rating_name == "Hard"
        assert previews[3].rating_name == "Good"
        assert previews[4].rating_name == "Easy"

    def test_preview_option_has_new_interval(self):
        """PreviewOption should have new_interval attribute."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert hasattr(previews[rating], "new_interval")
            assert isinstance(previews[rating].new_interval, int)
            assert previews[rating].new_interval > 0

    def test_preview_option_has_new_stability(self):
        """PreviewOption should have new_stability attribute."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert hasattr(previews[rating], "new_stability")
            assert isinstance(previews[rating].new_stability, float)

    def test_preview_option_has_new_difficulty(self):
        """PreviewOption should have new_difficulty attribute."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert hasattr(previews[rating], "new_difficulty")
            assert isinstance(previews[rating].new_difficulty, float)

    def test_preview_option_has_new_state(self):
        """PreviewOption should have new_state attribute."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert hasattr(previews[rating], "new_state")
            assert isinstance(previews[rating].new_state, str)
            assert previews[rating].new_state in ["new", "learning", "review", "relearning"]


class TestIntervalOrdering:
    """Test that intervals follow expected ordering."""

    def test_intervals_increase_with_rating(self):
        """Higher ratings should generally have longer intervals."""
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
        previews = preview_schedule(state)

        # Again should have shortest or equal interval
        # Easy should have longest interval
        assert previews[1].new_interval <= previews[2].new_interval
        assert previews[2].new_interval <= previews[3].new_interval
        assert previews[3].new_interval <= previews[4].new_interval

    def test_intervals_monotonic_for_learning_cards(self):
        """Intervals should be monotonic for learning cards too."""
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
        previews = preview_schedule(state)

        # Should still be monotonically increasing
        assert previews[1].new_interval <= previews[2].new_interval
        assert previews[2].new_interval <= previews[3].new_interval
        assert previews[3].new_interval <= previews[4].new_interval


class TestPreviewMatchesScheduler:
    """Test that preview matches what schedule_review() produces."""

    def test_preview_matches_actual_schedule(self):
        """Preview should match what schedule_review() returns."""
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
        previews = preview_schedule(state)

        # For each rating, verify preview matches actual outcome
        for rating in [1, 2, 3, 4]:
            actual_outcome = schedule_review(state, rating)
            preview = previews[rating]

            assert preview.new_interval == actual_outcome.new_interval
            assert preview.new_stability == actual_outcome.new_stability
            assert preview.new_difficulty == actual_outcome.new_difficulty
            assert preview.new_state == actual_outcome.new_state

    def test_preview_matches_scheduler_for_new_cards(self):
        """Preview should match scheduler for new cards."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            actual = schedule_review(state, rating)
            preview = previews[rating]

            assert preview.new_state == actual.new_state
            assert preview.new_interval == actual.new_interval

    def test_preview_matches_scheduler_for_learning_cards(self):
        """Preview should match scheduler for learning cards."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            actual = schedule_review(state, rating)
            preview = previews[rating]

            assert preview.new_state == actual.new_state

    def test_preview_matches_scheduler_for_relearning_cards(self):
        """Preview should match scheduler for relearning cards."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            actual = schedule_review(state, rating)
            preview = previews[rating]

            assert preview.new_state == actual.new_state


class TestNewCardStates:
    """Test preview for new cards."""

    def test_preview_with_new_card(self):
        """Preview should work for new cards."""
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
        previews = preview_schedule(state)

        assert len(previews) == 4
        # New card with Again should enter learning
        assert previews[1].new_state == "learning"
        # New card with Hard should enter learning
        assert previews[2].new_state == "learning"
        # New card with Good should enter review
        assert previews[3].new_state == "review"
        # New card with Easy should enter review
        assert previews[4].new_state == "review"


class TestCustomParameters:
    """Test preview with custom parameters."""

    def test_preview_with_custom_parameters(self):
        """Preview should accept custom FSRS parameters."""
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
        custom_params = FSRSParameters(
            w=FSRSParameters.default().w,
            request_retention=0.95,  # Higher retention
            maximum_interval=10000,
        )
        previews = preview_schedule(state, custom_params)

        assert len(previews) == 4

    def test_preview_with_different_retention_rate(self):
        """Preview should use custom retention rate in calculations."""
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

        # Default parameters (90% retention)
        default_params = FSRSParameters.default()
        previews_default = preview_schedule(state, default_params)

        # Higher retention (95%) - want to test that different retention rates affect intervals
        high_retention_params = FSRSParameters(
            w=default_params.w,
            request_retention=0.95,
            maximum_interval=default_params.maximum_interval,
        )
        previews_high = preview_schedule(state, high_retention_params)

        # Lower retention rate (90%) means we're OK with more forgetting,
        # so intervals can be longer. Higher retention (95%) means we want
        # to review more frequently, so intervals should be shorter.
        assert previews_default[3].new_interval > previews_high[3].new_interval


class TestStabilityDifferences:
    """Test that ratings show different stability outcomes."""

    def test_preview_stability_differences(self):
        """Preview should show how ratings affect stability."""
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
        previews = preview_schedule(state)

        # Higher ratings should increase stability more
        assert previews[1].new_stability < previews[2].new_stability
        assert previews[2].new_stability < previews[3].new_stability
        assert previews[3].new_stability < previews[4].new_stability

    def test_preview_stability_for_new_cards(self):
        """Preview should show stability increases for all ratings on new cards."""
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
        previews = preview_schedule(state)

        # All should have positive stability
        assert previews[1].new_stability > 0.0
        assert previews[2].new_stability > 0.0
        assert previews[3].new_stability > 0.0
        assert previews[4].new_stability > 0.0


class TestDifficultyChanges:
    """Test that ratings show different difficulty outcomes."""

    def test_preview_difficulty_changes(self):
        """Preview should show how ratings affect difficulty."""
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
        previews = preview_schedule(state)

        # Hard should increase difficulty
        assert previews[2].new_difficulty > 5.0
        # Good should keep difficulty relatively stable
        assert abs(previews[3].new_difficulty - 5.0) < 0.5
        # Easy should decrease difficulty
        assert previews[4].new_difficulty < 5.0

    def test_preview_difficulty_bounded(self):
        """Difficulty should always be in [1, 10] range."""
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
        previews = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert 1.0 <= previews[rating].new_difficulty <= 10.0


class TestStateImmutability:
    """Test that preview does not modify the input state."""

    def test_preview_does_not_modify_state(self):
        """Calling preview should not modify the input state."""
        original_state = CardState(
            stability=10.0,
            difficulty=5.0,
            elapsed_days=5.0,
            scheduled_days=10.0,
            reps=3,
            lapses=0,
            state="review",
            last_review=datetime.now(),
        )

        # Store original values
        original_stability = original_state.stability
        original_difficulty = original_state.difficulty
        original_reps = original_state.reps
        original_lapses = original_state.lapses
        original_state_str = original_state.state

        preview_schedule(original_state)

        # Verify state unchanged
        assert original_state.stability == original_stability
        assert original_state.difficulty == original_difficulty
        assert original_state.reps == original_reps
        assert original_state.lapses == original_lapses
        assert original_state.state == original_state_str

    def test_preview_multiple_calls_consistent(self):
        """Multiple preview calls on same state should give same results."""
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

        previews1 = preview_schedule(state)
        previews2 = preview_schedule(state)

        for rating in [1, 2, 3, 4]:
            assert previews1[rating].new_interval == previews2[rating].new_interval
            assert previews1[rating].new_stability == previews2[rating].new_stability
            assert previews1[rating].new_difficulty == previews2[rating].new_difficulty


class TestDefaultParameters:
    """Test preview with default parameters."""

    def test_preview_with_default_parameters(self):
        """Preview should work without explicit parameters."""
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
        previews = preview_schedule(state)

        assert len(previews) == 4
        assert all(isinstance(p, PreviewOption) for p in previews.values())

    def test_preview_default_matches_explicit_default(self):
        """Preview with no params should match preview with explicit default params."""
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

        previews_default = preview_schedule(state)
        previews_explicit = preview_schedule(state, FSRSParameters.default())

        for rating in [1, 2, 3, 4]:
            assert previews_default[rating].new_interval == previews_explicit[rating].new_interval
            assert previews_default[rating].new_stability == previews_explicit[rating].new_stability


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_preview_with_very_high_stability(self):
        """Preview should handle very high stability values."""
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
        previews = preview_schedule(state)

        assert len(previews) == 4
        # Should be capped at maximum_interval
        params = FSRSParameters.default()
        for rating in [1, 2, 3, 4]:
            assert previews[rating].new_interval <= params.maximum_interval

    def test_preview_with_zero_elapsed_days(self):
        """Preview should handle zero elapsed_days."""
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
        previews = preview_schedule(state)

        assert len(previews) == 4

    def test_preview_with_many_lapses(self):
        """Preview should handle cards with many lapses."""
        state = CardState(
            stability=5.0,
            difficulty=9.0,
            elapsed_days=1.0,
            scheduled_days=2.0,
            reps=5,
            lapses=10,
            state="relearning",
            last_review=datetime.now(),
        )
        previews = preview_schedule(state)

        assert len(previews) == 4
        for rating in [1, 2, 3, 4]:
            assert previews[rating].new_interval > 0
