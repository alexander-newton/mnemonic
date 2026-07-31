"""Tests for the pure variation chooser."""

from __future__ import annotations

from datetime import datetime

from mnemonic.core.variation.choose import VariationCandidate, choose_variation


def _cand(vid: str, *, shown: int = 0, when: datetime | None = None) -> VariationCandidate:
    return VariationCandidate(
        variation_id=vid,
        question=f"q-{vid}",
        answer=f"a-{vid}",
        shown_count=shown,
        generated_at=when or datetime(2026, 7, 1, 12, 0, 0),
    )


def test_disabled_returns_none():
    assert choose_variation([_cand("v1")], enabled=False, frequency=1.0, roll=0.0) is None


def test_empty_candidates_returns_none():
    assert choose_variation([], enabled=True, frequency=1.0, roll=0.0) is None


def test_roll_at_or_above_frequency_returns_none():
    assert choose_variation([_cand("v1")], enabled=True, frequency=0.3, roll=0.3) is None
    assert choose_variation([_cand("v1")], enabled=True, frequency=0.3, roll=0.9) is None


def test_frequency_one_always_picks():
    got = choose_variation([_cand("v1")], enabled=True, frequency=1.0, roll=0.999)
    assert got is not None and got.variation_id == "v1"


def test_frequency_zero_never_picks():
    assert choose_variation([_cand("v1")], enabled=True, frequency=0.0, roll=0.0) is None


def test_lowest_shown_count_wins():
    got = choose_variation(
        [_cand("v1", shown=5), _cand("v2", shown=1), _cand("v3", shown=9)],
        enabled=True,
        frequency=1.0,
        roll=0.0,
    )
    assert got is not None and got.variation_id == "v2"


def test_tie_on_shown_count_breaks_to_newest():
    got = choose_variation(
        [
            _cand("old", shown=2, when=datetime(2026, 7, 1)),
            _cand("new", shown=2, when=datetime(2026, 7, 10)),
        ],
        enabled=True,
        frequency=1.0,
        roll=0.0,
    )
    assert got is not None and got.variation_id == "new"


def test_full_tie_breaks_stably_by_id():
    same = datetime(2026, 7, 5)
    got = choose_variation(
        [_cand("bbb", shown=1, when=same), _cand("aaa", shown=1, when=same)],
        enabled=True,
        frequency=1.0,
        roll=0.0,
    )
    assert got is not None and got.variation_id == "aaa"


def test_frequency_is_clamped():
    # frequency > 1 behaves as 1.0 (always), frequency < 0 behaves as 0.0 (never)
    assert choose_variation([_cand("v1")], enabled=True, frequency=5.0, roll=0.99) is not None
    assert choose_variation([_cand("v1")], enabled=True, frequency=-2.0, roll=0.0) is None


def test_returns_the_candidate_text():
    got = choose_variation([_cand("v1")], enabled=True, frequency=1.0, roll=0.0)
    assert got is not None
    assert got.question == "q-v1" and got.answer == "a-v1"
