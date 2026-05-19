"""Core FSRS algorithm implementation.

This module implements the core FSRS (Free Spaced Repetition Scheduler)
algorithm for calculating memory retention and scheduling reviews.

The algorithm is based on research into optimal spacing and follows
the "NO SILENT FAILURES" principle - all errors are informative.

Reference: https://github.com/open-spaced-repetition/fsrs4py
"""

import math

from mnemonic.core.fsrs.parameters import FSRSParameters


def calculate_retrievability(
    stability: float,
    elapsed_days: float,
    parameters: FSRSParameters | None = None,
) -> float:
    """Calculate current retrievability given stability and elapsed time.

    Retrievability is the probability that a card can be recalled correctly.
    It decays exponentially as time passes since the last review.

    The FSRS formula is: R = exp(ln(retention) * elapsed_days / stability)

    Where:
    - R is retrievability (0 to 1, where 1 is perfectly remembered)
    - retention is the target retention rate (default 0.9)
    - stability is how long memory takes to decay to the target rate
    - elapsed_days is time since the last review

    Args:
        stability: Memory stability in days. How long until retrievability
            decays to the target retention rate. Must be positive.
        elapsed_days: Days since the last review. Must be non-negative.
        parameters: FSRS parameters (uses default FSRS-5 if None)

    Returns:
        float: Retrievability between 0.0 and 1.0, where:
            - 1.0 = card was just reviewed (perfect recall)
            - 0.9 = at the stability interval (target retention)
            - 0.0 = card was forgotten long ago

    Raises:
        ValueError: If stability <= 0 or elapsed_days < 0.
            Error messages are informative per "NO SILENT FAILURES" principle.

    Examples:
        >>> r = calculate_retrievability(10.0, 0.0)
        >>> abs(r - 1.0) < 0.0001  # Just reviewed
        True

        >>> r = calculate_retrievability(10.0, 10.0)
        >>> abs(r - 0.9) < 0.01  # At stability interval
        True

        >>> r = calculate_retrievability(10.0, 20.0)
        >>> 0.0 < r < 0.9  # Forgotten some
        True
    """
    # Input validation - must fail loudly per project principles
    if stability <= 0:
        raise ValueError(
            f"stability must be positive, got {stability}. "
            "Stability represents memory half-life in days and cannot be zero or negative."
        )

    if elapsed_days < 0:
        raise ValueError(
            f"elapsed_days must be non-negative, got {elapsed_days}. "
            "Time cannot go backwards. Check that your review timestamp is after the last review."
        )

    # Use default parameters if none provided
    if parameters is None:
        parameters = FSRSParameters.default()

    # FSRS formula: R = exp(ln(retention) * elapsed_days / stability)
    # This implements exponential decay where:
    # - At elapsed_days=0: R = exp(0) = 1.0 (perfect memory)
    # - At elapsed_days=stability: R = exp(ln(retention)) = retention (e.g., 0.9)
    # - As elapsed_days increases: R approaches 0 (forgotten)

    ln_retention = math.log(parameters.request_retention)
    exponent = ln_retention * elapsed_days / stability
    retrievability = math.exp(exponent)

    return retrievability
