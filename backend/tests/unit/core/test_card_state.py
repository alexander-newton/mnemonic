"""Tests for the shared CardState builder."""

from __future__ import annotations

from datetime import datetime

from mnemonic.core.fsrs.state import to_card_state


def test_new_card_has_zero_elapsed_and_no_last_review():
    now = datetime(2026, 7, 9, 12, 0, 0)
    st = to_card_state(
        stability=0.0,
        difficulty=5.0,
        reps=0,
        lapses=0,
        state="new",
        due=None,
        last_review=None,
        now=now,
    )
    assert st.elapsed_days == 0.0 and st.scheduled_days == 0.0 and st.last_review is None
    assert st.state == "new" and st.difficulty == 5.0


def test_elapsed_and_scheduled_derived_from_last_review():
    now = datetime(2026, 7, 9, 12, 0, 0)
    last = datetime(2026, 7, 4, 12, 0, 0)  # 5 days before now
    due = datetime(2026, 7, 8, 12, 0, 0)  # 4 days after last
    st = to_card_state(
        stability=10.0,
        difficulty=6.0,
        reps=3,
        lapses=1,
        state="review",
        due=due,
        last_review=last,
        now=now,
    )
    assert st.elapsed_days == 5.0
    assert st.scheduled_days == 4.0
    assert st.last_review == last
