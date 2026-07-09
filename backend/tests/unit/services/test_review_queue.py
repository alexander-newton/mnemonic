"""Tests for the review-queue policy and service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.services.review_queue import SimplePolicy
from mnemonic.vault.repository import Card

NOW = datetime(2026, 7, 9, 12, 0, 0)


def _card(cid, *, state="review", due=None, suspended=False):
    return Card(
        card_id=cid,
        note_path=Path("n.qmd"),
        deck_folder=Path("gt"),
        syntax="cloze",
        front="f",
        back="b",
        title="t",
        state=state,
        stability=1.0,
        difficulty=5.0,
        due=due,
        reps=0,
        lapses=0,
        leech_score=0.0,
        suspended=suspended,
        core_changed=False,
        core_changed_at=None,
    )


def test_due_cards_ordered_by_due_then_new_appended():
    cards = [
        _card("new1", state="new"),
        _card("due-late", due=datetime(2026, 7, 9, 10, 0, 0)),
        _card("due-early", due=datetime(2026, 7, 8, 10, 0, 0)),
    ]
    out = SimplePolicy().build_queue(cards, NOW, daily_new_limit=10)
    assert [c.card_id for c in out] == ["due-early", "due-late", "new1"]


def test_suspended_and_future_due_excluded():
    cards = [
        _card("suspended", due=datetime(2026, 7, 8, 0, 0, 0), suspended=True),
        _card("future", due=datetime(2026, 7, 20, 0, 0, 0)),
        _card("due", due=datetime(2026, 7, 9, 0, 0, 0)),
    ]
    out = SimplePolicy().build_queue(cards, NOW, daily_new_limit=10)
    assert [c.card_id for c in out] == ["due"]


def test_new_cards_capped_by_daily_new_limit():
    cards = [_card(f"new{i}", state="new") for i in range(5)]
    out = SimplePolicy().build_queue(cards, NOW, daily_new_limit=2)
    assert len(out) == 2 and all(c.state == "new" for c in out)
