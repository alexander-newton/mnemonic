"""Build a DSPy trainset from finalized, reward-labeled TrainingExamples."""

from __future__ import annotations

import random
from typing import TypeVar

import dspy
from sqlalchemy import select
from sqlalchemy.orm import Session

from mnemonic.config import OptimizationConfig
from mnemonic.db.models import PromptVersion, TrainingExample
from mnemonic.exceptions import InsufficientDataError

T = TypeVar("T")


def build_trainset(
    session: Session, *, strategy: str, config: OptimizationConfig
) -> list[dspy.Example]:
    """Build dspy.Examples for a strategy from finalized, rewarded examples.

    Args:
        session: Active SQLAlchemy session.
        strategy: Strategy name (resolved via PromptVersion.prompt_version_id).
        config: Optimization config (provides ``min_examples_to_compile``).

    Returns:
        A list of dspy.Example with base_q/base_a/note_context inputs, the
        historical variation as question/answer, and the gold ``reward``.

    Raises:
        InsufficientDataError: If fewer than ``min_examples_to_compile`` rows
            qualify.
    """
    rows = session.execute(
        select(TrainingExample)
        .join(PromptVersion, TrainingExample.prompt_version_id == PromptVersion.id)
        .where(
            PromptVersion.strategy == strategy,
            TrainingExample.finalized.is_(True),
            TrainingExample.reward.is_not(None),
        )
        .order_by(TrainingExample.created_at.asc(), TrainingExample.id.asc())
    ).scalars().all()

    if len(rows) < config.min_examples_to_compile:
        raise InsufficientDataError(
            strategy, have=len(rows), need=config.min_examples_to_compile
        )

    examples: list[dspy.Example] = []
    for row in rows:
        examples.append(
            dspy.Example(
                base_q=row.base_q,
                base_a=row.base_a,
                note_context=row.note_context or "",
                question=row.variation_q,
                answer=row.variation_a,
                reward=float(row.reward),
            ).with_inputs("base_q", "base_a", "note_context")
        )
    return examples


def split_examples(
    items: list[T], *, val_fraction: float, seed: int
) -> tuple[list[T], list[T]]:
    """Deterministically shuffle and split items into (train, val).

    Args:
        items: The full list to split.
        val_fraction: Fraction of items to place in the validation split.
        seed: RNG seed for reproducibility.

    Returns:
        A (train, val) tuple. ``val`` gets ``floor(len*val_fraction)`` items.
    """
    shuffled = list(items)
    random.Random(seed).shuffle(shuffled)
    n_val = int(len(shuffled) * val_fraction)
    val = shuffled[:n_val]
    train = shuffled[n_val:]
    return train, val
