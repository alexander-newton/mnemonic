"""FSRS preview function that shows outcomes for all ratings.

This module provides the preview_schedule() function that allows users to see
what will happen if they choose each of the four ratings before committing to
a review. This helps users make informed decisions about how to rate their
recall difficulty.

The preview does not modify the card state and always reflects the actual
outcome that schedule_review() would produce for each rating.
"""

from dataclasses import dataclass

from mnemonic.core.fsrs.models import CardState
from mnemonic.core.fsrs.parameters import FSRSParameters
from mnemonic.core.fsrs.scheduler import schedule_review


@dataclass
class PreviewOption:
    """Preview of what will happen if a rating is chosen.

    This data structure represents the predicted outcome if the user chooses
    a specific rating during a review. It includes all the information needed
    to display the consequences of each rating choice to the user.

    Attributes:
        rating: The rating number (1-4).
            - 1 = "Again" (failed recall)
            - 2 = "Hard" (difficult but correct)
            - 3 = "Good" (correct and smooth)
            - 4 = "Easy" (very easy recall)
        rating_name: Human-readable name for the rating.
        new_interval: Days until next review if this rating is chosen.
        new_stability: Updated memory stability (days) after this rating.
        new_difficulty: Updated card difficulty (1-10 scale) after this rating.
        new_state: Updated learning state after this rating
            (new/learning/review/relearning).
    """

    rating: int
    rating_name: str
    new_interval: int
    new_stability: float
    new_difficulty: float
    new_state: str


def preview_schedule(
    current_state: CardState,
    parameters: FSRSParameters | None = None,
) -> dict[int, PreviewOption]:
    """Preview scheduling outcomes for all four ratings.

    This function allows users to see what will happen if they choose each
    rating before committing to a review. It returns a dictionary mapping
    each rating (1-4) to a PreviewOption describing the consequences.

    The preview uses the same scheduling algorithm as schedule_review(),
    so the results are guaranteed to match what actually happens when the
    user chooses a rating.

    This function does not modify the input state. It can be called multiple
    times on the same state and will produce consistent results.

    Args:
        current_state: Current card state (stability, difficulty, etc.).
        parameters: FSRS parameters (uses default FSRS-5 if None).

    Returns:
        Dictionary mapping rating (1-4) to PreviewOption describing the
        outcome if that rating is chosen. Keys are always 1, 2, 3, 4.

    Examples:
        >>> state = CardState(
        ...     stability=10.0,
        ...     difficulty=5.0,
        ...     elapsed_days=5.0,
        ...     scheduled_days=10.0,
        ...     reps=3,
        ...     lapses=0,
        ...     state="review",
        ...     last_review=datetime.now()
        ... )
        >>> previews = preview_schedule(state)
        >>> print(f"Again: {previews[1].new_interval} days")
        >>> print(f"Good: {previews[3].new_interval} days")
        >>> print(f"Easy: {previews[4].new_interval} days")

        The intervals typically follow: Again < Hard < Good < Easy
    """
    # Use default parameters if not provided
    if parameters is None:
        parameters = FSRSParameters.default()

    # Rating names for user display
    rating_names = {
        1: "Again",
        2: "Hard",
        3: "Good",
        4: "Easy",
    }

    # Generate preview for each rating
    previews = {}
    for rating in [1, 2, 3, 4]:
        # Calculate what would happen with this rating
        outcome = schedule_review(current_state, rating, parameters)

        # Create preview option with human-readable name
        previews[rating] = PreviewOption(
            rating=rating,
            rating_name=rating_names[rating],
            new_interval=outcome.new_interval,
            new_stability=outcome.new_stability,
            new_difficulty=outcome.new_difficulty,
            new_state=outcome.new_state,
        )

    return previews
