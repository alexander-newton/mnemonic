"""Tests for the validity check and reward-weighted metric."""

from __future__ import annotations

import dspy

from mnemonic.core.optimization.metric import is_valid_variation, reward_metric


def _example(reward, base_q="What is X?", base_a="X is Y."):
    return dspy.Example(
        base_q=base_q, base_a=base_a, note_context="ctx",
        question="gold q", answer="gold a", reward=reward,
    ).with_inputs("base_q", "base_a", "note_context")


def _pred(question, answer):
    return dspy.Prediction(question=question, answer=answer)


def test_is_valid_rejects_empty_fields():
    assert is_valid_variation(base_q="q", base_a="a", question="", answer="x") is False
    assert is_valid_variation(base_q="q", base_a="a", question="x", answer="") is False


def test_is_valid_rejects_verbatim_duplicate_of_base():
    assert is_valid_variation(
        base_q="What is X?", base_a="X is Y.",
        question="What is X?", answer="X is Y.",
    ) is False


def test_is_valid_accepts_a_distinct_well_formed_variation():
    assert is_valid_variation(
        base_q="What is X?", base_a="X is Y.",
        question="Define X.", answer="It is Y.",
    ) is True


def test_metric_zero_for_invalid_prediction():
    ex = _example(reward=0.8)
    assert reward_metric(ex, _pred("", "a")) == 0.0


def test_metric_returns_clamped_reward_for_valid_prediction():
    ex = _example(reward=0.8)
    assert reward_metric(ex, _pred("Define X.", "It is Y.")) == 0.8


def test_metric_clamps_negative_reward_to_zero():
    ex = _example(reward=-0.5)
    assert reward_metric(ex, _pred("Define X.", "It is Y.")) == 0.0
