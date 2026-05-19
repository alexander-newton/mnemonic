"""Tests for FSRS (Free Spaced Repetition Scheduler) algorithm.

This module tests the core FSRS algorithm following strict TDD principles.
All tests are written BEFORE implementation to define expected behavior.

The FSRS algorithm predicts memory retention and schedules reviews optimally.
Key concepts:
- Stability (S): How long until retrievability drops to 90%
- Difficulty (D): How hard the card is (0-10 scale, higher = harder)
- Retrievability (R): Current probability of recall (0-1)
"""

import pytest

from mnemonic.core.fsrs.algorithm import calculate_retrievability
from mnemonic.core.fsrs.parameters import FSRSParameters


class TestFSRSParametersClass:
    """Test FSRSParameters class for FSRS-5 configuration."""

    def test_fsrs_parameters_has_w_weights(self):
        """Test that FSRSParameters has w attribute with weights."""
        params = FSRSParameters.default()
        assert hasattr(params, "w")
        assert isinstance(params.w, list)

    def test_fsrs_parameters_has_19_weights(self):
        """Test that FSRSParameters has exactly 19 weights from FSRS-5."""
        params = FSRSParameters.default()
        assert len(params.w) == 19, "FSRS-5 requires 19 weights"

    def test_fsrs_parameters_default_request_retention(self):
        """Test that default request_retention is 0.9."""
        params = FSRSParameters.default()
        assert params.request_retention == 0.9

    def test_fsrs_parameters_default_maximum_interval(self):
        """Test that default maximum_interval is 36500 days."""
        params = FSRSParameters.default()
        assert params.maximum_interval == 36500

    def test_fsrs_parameters_weights_are_floats(self):
        """Test that all weights are floats."""
        params = FSRSParameters.default()
        for w in params.w:
            assert isinstance(w, float), f"Weight {w} is not a float"

    def test_fsrs_parameters_weights_are_positive(self):
        """Test that all weights are positive."""
        params = FSRSParameters.default()
        for w in params.w:
            assert w > 0, f"Weight {w} is not positive"

    def test_fsrs_parameters_default_is_reproducible(self):
        """Test that calling default() multiple times gives same parameters."""
        params1 = FSRSParameters.default()
        params2 = FSRSParameters.default()
        assert params1.w == params2.w
        assert params1.request_retention == params2.request_retention
        assert params1.maximum_interval == params2.maximum_interval

    def test_fsrs_parameters_custom_construction(self):
        """Test that FSRSParameters can be constructed with custom values."""
        custom_weights = [0.5] * 19
        params = FSRSParameters(w=custom_weights, request_retention=0.85, maximum_interval=10000)
        assert params.w == custom_weights
        assert params.request_retention == 0.85
        assert params.maximum_interval == 10000


class TestCalculateRetrievability:
    """Test calculate_retrievability function for memory retention."""

    def test_retrievability_at_zero_elapsed_days(self):
        """Retrievability should be 1.0 immediately after review."""
        r = calculate_retrievability(10.0, 0.0)
        assert abs(r - 1.0) < 0.0001, "Retrievability at t=0 must be 1.0"

    def test_retrievability_decreases_over_time(self):
        """Retrievability should decrease monotonically as time passes."""
        r0 = calculate_retrievability(10.0, 0.0)
        r5 = calculate_retrievability(10.0, 5.0)
        r10 = calculate_retrievability(10.0, 10.0)
        r20 = calculate_retrievability(10.0, 20.0)
        assert r0 > r5 > r10 > r20, "Retrievability must decrease over time"

    def test_retrievability_at_stability_equals_target_retention(self):
        """At elapsed_days == stability, R should equal target retention."""
        # FSRS formula: R = exp(ln(0.9) * elapsed_days / stability)
        # When elapsed_days == stability: R = exp(ln(0.9)) = 0.9
        r = calculate_retrievability(10.0, 10.0)
        assert abs(r - 0.9) < 0.01, "At t=stability, R should be 0.9"

    def test_retrievability_at_stability_equals_default_retention(self):
        """At elapsed_days == stability, R should equal default retention (0.9)."""
        for stability in [5.0, 10.0, 20.0, 50.0, 100.0]:
            r = calculate_retrievability(stability, stability)
            assert abs(r - 0.9) < 0.01, f"At stability {stability}, R should be 0.9"

    def test_higher_stability_slower_decay(self):
        """Cards with higher stability decay slower."""
        # At the same elapsed time, higher stability means higher retrievability
        r_low_stability = calculate_retrievability(5.0, 5.0)
        r_high_stability = calculate_retrievability(10.0, 5.0)
        assert r_high_stability > r_low_stability, "Higher stability should result in slower decay"

    def test_retrievability_approaches_zero_over_infinite_time(self):
        """Retrievability should approach 0 as elapsed_days -> infinity."""
        r_very_long = calculate_retrievability(10.0, 1000.0)
        assert 0.0 < r_very_long < 0.001, "After 1000 days, R should be near 0"

    def test_retrievability_range(self):
        """Retrievability should always be in range [0, 1]."""
        test_cases = [
            (5.0, 0.0),
            (10.0, 5.0),
            (20.0, 10.0),
            (100.0, 50.0),
            (1.0, 100.0),
        ]
        for stability, elapsed in test_cases:
            r = calculate_retrievability(stability, elapsed)
            assert 0.0 <= r <= 1.0, (
                f"Retrievability must be in [0, 1], got {r} "
                f"for stability={stability}, elapsed={elapsed}"
            )

    def test_raises_error_for_negative_stability(self):
        """Should raise ValueError for negative stability."""
        with pytest.raises(ValueError) as exc_info:
            calculate_retrievability(-1.0, 5.0)
        assert "stability" in str(exc_info.value).lower()

    def test_raises_error_for_zero_stability(self):
        """Should raise ValueError for zero stability."""
        with pytest.raises(ValueError) as exc_info:
            calculate_retrievability(0.0, 5.0)
        assert "stability" in str(exc_info.value).lower()

    def test_raises_error_for_negative_elapsed_days(self):
        """Should raise ValueError for negative elapsed_days."""
        with pytest.raises(ValueError) as exc_info:
            calculate_retrievability(10.0, -1.0)
        assert "elapsed" in str(exc_info.value).lower()

    def test_raises_error_for_negative_elapsed_days_specific_message(self):
        """Error message should explain why negative time is invalid."""
        with pytest.raises(ValueError) as exc_info:
            calculate_retrievability(10.0, -5.0)
        error_msg = str(exc_info.value).lower()
        assert "negative" in error_msg or "elapsed" in error_msg

    def test_accepts_very_small_positive_values(self):
        """Should accept very small but positive stability and elapsed values."""
        r1 = calculate_retrievability(0.001, 0.0001)
        assert 0.0 < r1 <= 1.0

    def test_accepts_very_large_values(self):
        """Should accept very large stability values."""
        r = calculate_retrievability(100000.0, 50000.0)
        assert 0.0 < r <= 1.0

    def test_with_custom_parameters_accepted(self):
        """Should accept custom FSRS parameters."""
        params = FSRSParameters.default()
        r = calculate_retrievability(10.0, 5.0, params)
        assert 0.0 < r < 1.0

    def test_custom_parameters_used_in_calculation(self):
        """Custom request_retention should affect calculation."""
        params_default = FSRSParameters.default()
        params_high_retention = FSRSParameters(
            w=params_default.w,
            request_retention=0.95,  # Higher target
            maximum_interval=params_default.maximum_interval,
        )

        # With higher target retention, decay should be slower
        # (higher retrievability at same elapsed time)
        r_low = calculate_retrievability(10.0, 5.0, params_default)
        r_high = calculate_retrievability(10.0, 5.0, params_high_retention)
        # Higher retention target means less aggressive decay
        assert r_high > r_low

    def test_numerical_stability_with_edge_cases(self):
        """Test numerical stability with edge case values."""
        # Very long elapsed time
        r = calculate_retrievability(10.0, 10000.0)
        assert float("inf") not in [r] and float("-inf") not in [r]
        assert not any(char in str(r) for char in ["nan", "inf"])

    def test_float_parameters(self):
        """Should accept float parameters properly."""
        r1 = calculate_retrievability(10.5, 5.25)
        r2 = calculate_retrievability(10.5, 10.5)
        assert r1 > r2

    def test_consistency_across_calls(self):
        """Calling with same parameters should give same result."""
        r1 = calculate_retrievability(15.0, 7.5)
        r2 = calculate_retrievability(15.0, 7.5)
        assert r1 == r2, "Function must be deterministic"

    def test_default_parameters_optional(self):
        """Parameters argument should be optional."""
        r1 = calculate_retrievability(10.0, 5.0)
        r2 = calculate_retrievability(10.0, 5.0, None)
        r3 = calculate_retrievability(10.0, 5.0, FSRSParameters.default())
        assert r1 == r2 == r3

    def test_fsrs_formula_correctness(self):
        """Test FSRS formula: R = exp(ln(0.9) * elapsed_days / stability)."""
        import math

        stability = 20.0
        elapsed = 10.0
        expected = math.exp(math.log(0.9) * elapsed / stability)

        actual = calculate_retrievability(stability, elapsed)
        assert abs(actual - expected) < 0.0001, (
            f"Expected {expected}, got {actual} " f"(stability={stability}, elapsed={elapsed})"
        )

    def test_retrievability_with_various_parameter_combinations(self):
        """Test with diverse parameter combinations."""
        test_cases = [
            (1.0, 0.5),
            (1.0, 1.0),
            (1.0, 2.0),
            (5.0, 1.0),
            (5.0, 5.0),
            (5.0, 10.0),
            (100.0, 50.0),
            (100.0, 100.0),
            (100.0, 200.0),
        ]

        for stability, elapsed in test_cases:
            r = calculate_retrievability(stability, elapsed)
            assert (
                0.0 <= r <= 1.0
            ), f"Out of range for stability={stability}, elapsed={elapsed}: {r}"

            # Verify that at stability point, R ≈ 0.9
            if elapsed == stability:
                assert abs(r - 0.9) < 0.01

    def test_monotonic_decrease_property(self):
        """For fixed stability, increasing elapsed_days always decreases R."""
        stability = 10.0
        prev_r = calculate_retrievability(stability, 0.0)

        for elapsed in [1.0, 2.0, 3.0, 5.0, 10.0, 20.0, 50.0]:
            curr_r = calculate_retrievability(stability, elapsed)
            assert curr_r < prev_r, (
                f"R should decrease: prev={prev_r}, curr={curr_r} " f"at elapsed={elapsed}"
            )
            prev_r = curr_r

    def test_no_type_errors_with_int_inputs(self):
        """Should handle integer inputs gracefully."""
        r = calculate_retrievability(10, 5)  # ints instead of floats
        assert isinstance(r, float)
        assert 0.0 < r < 1.0
