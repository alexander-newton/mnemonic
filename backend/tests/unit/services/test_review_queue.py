"""Tests for the review-queue policy and service."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.core.policy.resolve import EffectivePolicy, Limits
from mnemonic.services.review_queue import DoneToday, QueueContext, RulesPolicy
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


def _policy(*, all_=Limits(), new=Limits(), due=Limits(), order="due_first", ine=None):
    return EffectivePolicy(all=all_, new=new, due=due, order=order, interleave_new_every=ine)


def _ctx(cards, policy, done=DoneToday(0, 0, 0), seed=0):
    return QueueContext(cards=cards, now=NOW, policy=policy, done_today=done, seed=seed)


def test_due_first_orders_due_by_due_then_new():
    cards = [
        _card("new1", state="new"),
        _card("due-late", due=datetime(2026, 7, 9, 10, 0, 0)),
        _card("due-early", due=datetime(2026, 7, 8, 10, 0, 0)),
    ]
    out = RulesPolicy().build_queue(_ctx(cards, _policy()))
    assert [c.card_id for c in out] == ["due-early", "due-late", "new1"]


def test_suspended_and_future_due_excluded():
    cards = [
        _card("suspended", due=datetime(2026, 7, 8, 0, 0, 0), suspended=True),
        _card("future", due=datetime(2026, 7, 20, 0, 0, 0)),
        _card("due", due=datetime(2026, 7, 9, 0, 0, 0)),
    ]
    out = RulesPolicy().build_queue(_ctx(cards, _policy()))
    assert [c.card_id for c in out] == ["due"]


def test_new_per_day_minus_done_today():
    cards = [_card(f"new{i}", state="new") for i in range(5)]
    policy = _policy(new=Limits(per_day=4))
    out = RulesPolicy().build_queue(_ctx(cards, policy, done=DoneToday(new=3, due=0, total=3)))
    assert len(out) == 1  # 4 per_day - 3 done = 1


def test_per_session_caps_new():
    cards = [_card(f"new{i}", state="new") for i in range(5)]
    out = RulesPolicy().build_queue(_ctx(cards, _policy(new=Limits(per_session=2))))
    assert len(out) == 2


def test_min_of_day_and_session_wins():
    cards = [_card(f"new{i}", state="new") for i in range(9)]
    policy = _policy(new=Limits(per_day=10, per_session=3))
    out = RulesPolicy().build_queue(_ctx(cards, policy, done=DoneToday(new=2, due=0, total=2)))
    assert len(out) == 3  # min(10-2, 3)


def test_over_budget_yields_zero():
    cards = [_card("new0", state="new")]
    policy = _policy(new=Limits(per_day=5))
    out = RulesPolicy().build_queue(_ctx(cards, policy, done=DoneToday(new=5, due=0, total=5)))
    assert out == []


def test_new_first_ordering():
    cards = [_card("d", due=datetime(2026, 7, 9, 0, 0, 0)), _card("n", state="new")]
    out = RulesPolicy().build_queue(_ctx(cards, _policy(order="new_first")))
    assert [c.card_id for c in out] == ["n", "d"]


def test_interleave_one_new_every_two_due():
    due = [_card(f"d{i}", due=datetime(2026, 7, i + 1, 0, 0, 0)) for i in range(4)]
    new = [_card(f"n{i}", state="new") for i in range(2)]
    out = RulesPolicy().build_queue(_ctx(due + new, _policy(order="interleave", ine=2)))
    assert [c.card_id for c in out] == ["d0", "d1", "n0", "d2", "d3", "n1"]


def test_shuffle_is_deterministic_for_seed():
    cards = [_card(f"d{i}", due=datetime(2026, 7, i + 1, 0, 0, 0)) for i in range(5)]
    a = RulesPolicy().build_queue(_ctx(cards, _policy(order="shuffle"), seed=7))
    b = RulesPolicy().build_queue(_ctx(cards, _policy(order="shuffle"), seed=7))
    assert [c.card_id for c in a] == [c.card_id for c in b]


def test_all_cap_trims_after_ordering():
    cards = [_card(f"d{i}", due=datetime(2026, 7, i + 1, 0, 0, 0)) for i in range(5)]
    out = RulesPolicy().build_queue(_ctx(cards, _policy(all_=Limits(per_day=2))))
    assert [c.card_id for c in out] == ["d0", "d1"]


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
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine,
        default_new_per_day=20,
        default_due_per_day=200,
    )

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
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine,
        default_new_per_day=20,
        default_due_per_day=200,
    )

    import pytest

    with pytest.raises(DeckNotFoundError):
        svc.build("nope")


def test_queue_service_honours_policy_toml(tmp_path):
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
    for i in range(4):
        (vault / "01_Projects" / "gt" / f"n{i}.qmd").write_text(
            f"---\ntitle: n{i}\n---\n## Card\n\nA {{{{c1::x}}}} card. ^card-n{i}\n"
        )
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text('[[rule]]\nscope = "new"\nper_day = 2\n')
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    svc = QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine,
        default_new_per_day=20,
        default_due_per_day=200,
    )

    items = svc.build("gt")

    assert len(items) == 2  # 4 new cards, policy.toml caps new per_day at 2
