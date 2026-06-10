"""Validity check and reward-weighted metric for DSPy compilation.

The metric gates demo/candidate selection on validity (well-formed, not a
verbatim copy of the base card) and weights by how much durable memory the gold
historical variation built (its Phase 1 reward, clamped to non-negative). It is
intentionally NOT a semantic prediction-vs-gold score — that is a future
extension; see the developer doc.
"""

from __future__ import annotations

from typing import Any


def is_valid_variation(*, base_q: str, base_a: str, question: str, answer: str) -> bool:
    """Return True if a generated variation is well-formed and non-trivial.

    Args:
        base_q: The base card question.
        base_a: The base card answer.
        question: The generated question.
        answer: The generated answer.

    Returns:
        False if either generated field is empty/whitespace, or if the generated
        Q and A both verbatim-match the base card (no variation). True otherwise.
    """
    if not question or not question.strip():
        return False
    if not answer or not answer.strip():
        return False
    duplicates_base = question.strip() == base_q.strip() and answer.strip() == base_a.strip()
    return not duplicates_base


def reward_metric(example: Any, pred: Any, _trace: Any = None) -> float:
    """Score a prediction: 0.0 if invalid, else the gold reward clamped to >= 0.

    Args:
        example: A dspy.Example carrying base_q/base_a and the gold ``reward``.
        pred: A dspy.Prediction with ``question`` and ``answer``.
        _trace: DSPy trace (unused; present for the optimizer's metric contract).

    Returns:
        A float score for the optimizer.
    """
    if not is_valid_variation(
        base_q=getattr(example, "base_q", ""),
        base_a=getattr(example, "base_a", ""),
        question=getattr(pred, "question", "") or "",
        answer=getattr(pred, "answer", "") or "",
    ):
        return 0.0
    return max(0.0, float(getattr(example, "reward", 0.0) or 0.0))
