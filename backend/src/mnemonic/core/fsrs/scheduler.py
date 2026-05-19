"""FSRS scheduler - calculates new card state after review.

This module implements the core scheduling logic that takes a card's
current FSRS state and a rating (1-4), then returns the new state
after applying FSRS-5 formulas.

The scheduler handles state transitions and parameter updates:
- new -> learning (failed) or review (successful)
- learning -> learning (failed) or review (successful)
- review -> relearning (failed) or review (successful)
- relearning -> relearning (failed) or review (successful)

All errors follow the "NO SILENT FAILURES" principle - errors are
informative and include context for debugging.
"""

import math

from mnemonic.core.fsrs.models import CardState, ReviewOutcome
from mnemonic.core.fsrs.parameters import FSRSParameters
from mnemonic.exceptions import InvalidRatingError


def schedule_review(
    current_state: CardState,
    rating: int,
    parameters: FSRSParameters | None = None,
) -> ReviewOutcome:
    """Calculate new card state after review.

    This is the main scheduler function that determines the next state
    of a card after a review with a given rating.

    The function:
    1. Validates the rating (must be 1, 2, 3, or 4)
    2. Calculates new stability, difficulty, and interval
    3. Determines the new learning state based on current state and rating
    4. Updates rep and lapse counters
    5. Returns the complete new state

    Args:
        current_state: Current card state with stability, difficulty, etc.
        rating: User rating (1=Again, 2=Hard, 3=Good, 4=Easy). Must be 1-4.
        parameters: FSRS parameters (uses default FSRS-5 if None).

    Returns:
        ReviewOutcome with new stability, difficulty, interval, state, etc.

    Raises:
        InvalidRatingError: If rating not in [1, 2, 3, 4]. Error message
            is informative, explaining valid ratings and implications.

    Examples:
        >>> state = CardState(
        ...     stability=10.0,
        ...     difficulty=5.0,
        ...     elapsed_days=5.0,
        ...     scheduled_days=10.0,
        ...     reps=2,
        ...     lapses=0,
        ...     state="review",
        ...     last_review=datetime.now()
        ... )
        >>> outcome = schedule_review(state, rating=3)
        >>> outcome.new_state
        'review'
        >>> outcome.new_interval > 0
        True
    """
    # Input validation
    if rating not in [1, 2, 3, 4]:
        raise InvalidRatingError(
            f"Rating must be 1-4 (1=Again, 2=Hard, 3=Good, 4=Easy), got {rating}. "
            "Rating reflects how well you recalled the card during review."
        )

    # Use default parameters if not provided
    if parameters is None:
        parameters = FSRSParameters.default()

    # Calculate retrievability before new interval
    retrievability = _calculate_retrievability(
        current_state.stability, current_state.elapsed_days, parameters
    )

    # Calculate new difficulty first, as it affects stability calculation
    new_difficulty = calculate_next_difficulty(current_state.difficulty, rating, parameters)

    # Calculate new stability using the new difficulty
    new_stability = calculate_next_stability(
        current_state.stability,
        new_difficulty,
        retrievability,
        rating,
        parameters,
    )

    new_interval = calculate_next_interval(new_stability, parameters)

    # Determine new state and update counters
    new_state = _determine_new_state(current_state.state, rating)
    new_reps = current_state.reps + (1 if rating >= 2 else 0)
    new_lapses = current_state.lapses + (1 if rating == 1 else 0)

    return ReviewOutcome(
        new_stability=new_stability,
        new_difficulty=new_difficulty,
        new_interval=new_interval,
        new_state=new_state,
        new_reps=new_reps,
        new_lapses=new_lapses,
    )


def calculate_next_stability(
    current_stability: float,
    current_difficulty: float,
    retrievability: float,
    rating: int,
    parameters: FSRSParameters,
) -> float:
    """Calculate new stability using FSRS-5 formula.

    The stability (memory half-life) is updated based on:
    - Current stability and difficulty
    - Retrievability before the review
    - The rating given by the user

    The FSRS-5 formulas handle three cases:
    1. New card (stability == 0): Use initial stability from weights w[rating-1]
    2. Successful review (rating >= 2): Stability increases
    3. Failed review (rating == 1): Stability decreases significantly

    Args:
        current_stability: Current memory stability (days).
        current_difficulty: Current card difficulty (1-10).
        retrievability: Current retrievability probability (0-1).
        rating: Review rating (1-4).
        parameters: FSRS parameters with 19 weights.

    Returns:
        float: New stability (days). Always positive.
    """
    # Handle new cards (stability = 0)
    if current_stability == 0:
        # Initial stability: S₀ = w[rating - 1]
        # Uses the weight corresponding to the rating
        return parameters.w[rating - 1]

    if rating == 1:
        # Failed review: S' = w[11] * D^(-w[12]) * ((S + 1)^w[13] - 1) * exp(w[14] * (1 - R))
        return (
            parameters.w[11]
            * math.pow(current_difficulty, -parameters.w[12])
            * (math.pow(current_stability + 1, parameters.w[13]) - 1)
            * math.exp(parameters.w[14] * (1 - retrievability))
        )
    else:
        # Successful review: S' = S * (exp(w[8]) * (11 - D) * S^(-w[9]) * (exp(w[10] * (1 - R)) - 1) + 1)
        return current_stability * (
            math.exp(parameters.w[8])
            * (11 - current_difficulty)
            * math.pow(current_stability, -parameters.w[9])
            * (math.exp(parameters.w[10] * (1 - retrievability)) - 1)
            + 1
        )


def calculate_next_difficulty(
    current_difficulty: float,
    rating: int,
    parameters: FSRSParameters,
) -> float:
    """Calculate new difficulty using FSRS-5 formula.

    Difficulty represents how hard the card is on a 1-10 scale.
    It is adjusted based on the rating:
    - Hard (rating=2): Difficulty increases
    - Good (rating=3): Difficulty barely changes (neutral rating)
    - Easy (rating=4): Difficulty decreases

    The formula is: D' = D - w[15] * (rating - 3)
    Which expands to:
    - rating=1: D' = D + 2*w[15] (large increase)
    - rating=2: D' = D + w[15] (increase)
    - rating=3: D' = D (no change)
    - rating=4: D' = D - w[15] (decrease)

    Then clamped to the range [1, 10].

    Args:
        current_difficulty: Current difficulty (1-10).
        rating: Review rating (1-4).
        parameters: FSRS parameters (uses w[15]).

    Returns:
        float: New difficulty, clamped to [1, 10].
    """
    # Calculate new difficulty: D' = D - w[15] * (rating - 3)
    new_difficulty = current_difficulty - parameters.w[15] * (rating - 3)

    # Clamp to valid range [1, 10]
    return max(1.0, min(10.0, new_difficulty))


def calculate_next_interval(
    stability: float,
    parameters: FSRSParameters,
) -> int:
    """Calculate interval (days) until next review.

    The interval is calculated from stability to achieve the target
    retention rate at the next review. The formula ensures that at the
    next scheduled review, retrievability will be at the target level.

    Formula: I = stability * (ln(request_retention) / ln(0.9))

    The interval is clamped to [1, maximum_interval] and rounded to
    the nearest integer (days).

    Args:
        stability: Memory stability (days).
        parameters: FSRS parameters with request_retention and maximum_interval.

    Returns:
        int: Interval in days. Minimum 1, maximum maximum_interval.
    """
    # Interval formula: I = S * (ln(request_retention) / ln(0.9))
    # This ensures that at the interval, retrievability = request_retention
    ln_retention = math.log(parameters.request_retention)
    ln_target = math.log(0.9)  # FSRS target (hard-coded for consistency)

    interval = stability * (ln_retention / ln_target)

    # Clamp to valid range and convert to integer days
    interval = max(1, min(int(round(interval)), parameters.maximum_interval))

    return interval


def _determine_new_state(current_state: str, rating: int) -> str:
    """Determine new learning state based on current state and rating.

    State transitions follow this logic:
    - "new" -> "learning" (all ratings) or "review" (rating >= 3)
    - "learning" -> "learning" (rating=1) or "review" (rating >= 2)
    - "review" -> "relearning" (rating=1) or "review" (rating >= 2)
    - "relearning" -> "relearning" (rating=1) or "review" (rating >= 2)

    Args:
        current_state: Current state (new/learning/review/relearning).
        rating: Review rating (1-4).

    Returns:
        str: New state (new/learning/review/relearning).
    """
    if current_state == "new":
        # New cards either stay in learning or move to review
        return "learning" if rating <= 2 else "review"
    elif current_state == "learning":
        # Learning cards stay in learning on failure, move to review on success
        return "learning" if rating == 1 else "review"
    elif current_state == "review":
        # Review cards move to relearning on failure, stay in review on success
        return "relearning" if rating == 1 else "review"
    else:  # relearning
        # Relearning cards stay in relearning on failure, move to review on success
        return "relearning" if rating == 1 else "review"


def _calculate_retrievability(
    stability: float,
    elapsed_days: float,
    parameters: FSRSParameters,
) -> float:
    """Calculate current retrievability (internal helper).

    This is an internal function that calculates the probability
    of successful recall before the review. Used to feed into
    the stability and difficulty calculations.

    Args:
        stability: Memory stability (days).
        elapsed_days: Days since last review.
        parameters: FSRS parameters with request_retention.

    Returns:
        float: Retrievability between 0 and 1.
    """
    if stability <= 0:
        return 1.0

    ln_retention = math.log(parameters.request_retention)
    exponent = ln_retention * elapsed_days / stability
    return math.exp(exponent)
