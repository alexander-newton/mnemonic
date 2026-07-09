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


def test_queue_service_builds_items(tmp_path):
    from mnemonic.db.models import Base
    from mnemonic.db.sqlite import create_engine
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "_deck.md").write_text(
        "---\ndeck_name: GT\nvariation_enabled: false\nvariation_frequency: 0.0\n"
        "leech_threshold: 8\ndaily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(repo=VaultRepository(vault_root=vault, engine=engine), engine=engine)

    items = svc.build("gt")

    assert len(items) == 1
    item = items[0]
    assert item.card_id == "card-aaaabbbb"
    assert item.front == "A [...] equilibrium."
    assert item.answer == "A **Nash** equilibrium."
    assert set(item.previews.keys()) == {1, 2, 3, 4}
    assert all(isinstance(v, int) for v in item.previews.values())


def test_queue_service_unknown_deck_raises(tmp_path):
    from mnemonic.db.models import Base
    from mnemonic.db.sqlite import create_engine
    from mnemonic.exceptions import DeckNotFoundError
    from mnemonic.services.review_queue import QueueService
    from mnemonic.vault.repository import VaultRepository

    vault = tmp_path / "vault"
    vault.mkdir()
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(repo=VaultRepository(vault_root=vault, engine=engine), engine=engine)

    import pytest

    with pytest.raises(DeckNotFoundError):
        svc.build("nope")
