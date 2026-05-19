"""FSRS (Free Spaced Repetition Scheduler) algorithm implementation.

This package provides the core FSRS algorithm for calculating memory
retention and scheduling optimal review intervals.

Key exports:
- FSRSParameters: Algorithm configuration with 19 FSRS-5 weights
- calculate_retrievability: Calculate current recall probability
- CardState: Data structure for card memory state
- ReviewOutcome: Data structure for review result
- schedule_review: Main scheduler function
- PreviewOption: Data structure for preview outcome
- preview_schedule: Preview all four rating outcomes
"""

from mnemonic.core.fsrs.algorithm import calculate_retrievability
from mnemonic.core.fsrs.models import CardState, ReviewOutcome
from mnemonic.core.fsrs.parameters import FSRSParameters
from mnemonic.core.fsrs.preview import PreviewOption, preview_schedule
from mnemonic.core.fsrs.scheduler import schedule_review

__all__ = [
    "FSRSParameters",
    "calculate_retrievability",
    "CardState",
    "ReviewOutcome",
    "schedule_review",
    "PreviewOption",
    "preview_schedule",
]
