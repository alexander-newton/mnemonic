"""Tests for CoreChangeService."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from mnemonic.db.models import Base, SchedulingState
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.services.core_change import CoreChangeService


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nThe {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def _flagged_row(engine, **overrides):
    fields = {
        "card_id": "card-aaaabbbb",
        "state": "review",
        "stability": 12.4,
        "difficulty": 6.1,
        "due": datetime(2026, 6, 20, 9, 0, 0),
        "reps": 5,
        "lapses": 1,
        "leech_score": 0.0,
        "core_changed": True,
        "core_changed_at": datetime(2026, 6, 12, 9, 0, 0),
    }
    fields.update(overrides)
    with session_scope(engine) as s:
        s.add(SchedulingState(**fields))


def _service(tmp_path):
    from mnemonic.vault.repository import VaultRepository

    vault, engine = _setup(tmp_path)
    repo = VaultRepository(vault_root=vault, engine=engine)
    return CoreChangeService(repo=repo, engine=engine), engine


NOW = datetime(2026, 6, 12, 12, 0, 0)


def test_keep_clears_flag_only(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    snap = svc.apply(card_id="card-aaaabbbb", decision="keep", now=NOW)
    assert snap.core_changed is False
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert bool(row.core_changed) is False
        assert row.core_changed_at is None
        assert row.stability == 12.4 and row.state == "review"  # FSRS untouched
        assert row.due == datetime(2026, 6, 20, 9, 0, 0)


def test_soft_reset_sets_due_now_preserves_memory(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    snap = svc.apply(card_id="card-aaaabbbb", decision="soft_reset", now=NOW)
    assert snap.due == NOW
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.due == NOW
        assert row.stability == 12.4 and row.difficulty == 6.1  # preserved
        assert row.reps == 5 and row.lapses == 1 and row.state == "review"
        assert bool(row.core_changed) is False


def test_full_reset_restores_defaults(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    snap = svc.apply(card_id="card-aaaabbbb", decision="full_reset", now=NOW)
    assert snap.state == "new" and snap.stability == 0.0 and snap.difficulty == 5.0
    assert snap.due is None and snap.reps == 0 and snap.lapses == 0
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.state == "new" and row.stability == 0.0 and row.difficulty == 5.0
        assert row.due is None and row.reps == 0 and row.lapses == 0
        assert bool(row.core_changed) is False


def test_apply_unflagged_card_raises(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine, core_changed=False, core_changed_at=None)
    with pytest.raises(CardNotFoundError):
        svc.apply(card_id="card-aaaabbbb", decision="keep", now=NOW)


def test_apply_missing_card_raises(tmp_path: Path):
    svc, _ = _service(tmp_path)
    with pytest.raises(CardNotFoundError):
        svc.apply(card_id="card-nope", decision="keep", now=NOW)


def test_apply_bad_decision_raises(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    with pytest.raises(ValidationError):
        svc.apply(card_id="card-aaaabbbb", decision="obliterate", now=NOW)


def test_list_changed_returns_only_flagged_with_kind(tmp_path: Path):
    from mnemonic.db.models import CoreChangeLog

    svc, engine = _service(tmp_path)
    _flagged_row(engine)  # card-aaaabbbb flagged, matches the seeded nash.qmd
    with session_scope(engine) as s:
        s.add(
            CoreChangeLog(
                id="log1",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )

    changed = svc.list_changed()

    assert len(changed) == 1
    item = changed[0]
    assert item.card_id == "card-aaaabbbb"
    assert item.title == "nash"
    assert item.change_kind == "material"
    assert item.stability == 12.4


def test_list_changed_uses_latest_change_kind(tmp_path: Path):
    from mnemonic.db.models import CoreChangeLog

    svc, engine = _service(tmp_path)
    _flagged_row(engine)
    with session_scope(engine) as s:
        s.add(
            CoreChangeLog(
                id="old",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 10, 9, 0, 0),
            )
        )
        s.add(
            CoreChangeLog(
                id="new",
                card_id="card-aaaabbbb",
                change_kind="cloze_structure",
                old_hash="o",
                new_hash="n",
                old_normalized="on",
                new_normalized="nn",
                detected_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )

    assert svc.list_changed()[0].change_kind == "cloze_structure"


def test_list_changed_empty_when_none_flagged(tmp_path: Path):
    svc, engine = _service(tmp_path)
    _flagged_row(engine, core_changed=False, core_changed_at=None)
    assert svc.list_changed() == []
