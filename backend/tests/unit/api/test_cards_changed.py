"""Tests for GET /api/cards/changed and POST /api/cards/{id}/core-change."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from fastapi.testclient import TestClient

from mnemonic.api.deps import get_core_change_service
from mnemonic.db.models import Base, CoreChangeLog, SchedulingState
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.main import app
from mnemonic.services.core_change import CoreChangeService
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nThe {{c1::Nash}} equilibrium. ^card-aaaabbbb\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def _flag(engine):
    with session_scope(engine) as s:
        s.add(
            SchedulingState(
                card_id="card-aaaabbbb",
                state="review",
                stability=12.4,
                difficulty=6.1,
                due=datetime(2026, 6, 20, 9, 0, 0),
                reps=5,
                lapses=1,
                leech_score=0.0,
                core_changed=True,
                core_changed_at=datetime(2026, 6, 12, 9, 0, 0),
            )
        )
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


def _override(vault, engine):
    app.dependency_overrides[get_core_change_service] = lambda: CoreChangeService(
        repo=VaultRepository(vault_root=vault, engine=engine), engine=engine
    )


def test_get_changed_returns_flagged_cards(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _flag(engine)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/cards/changed")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert len(body) == 1
    assert body[0]["card_id"] == "card-aaaabbbb"
    assert body[0]["change_kind"] == "material"
    assert body[0]["title"] == "nash"


def test_post_core_change_full_reset(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _flag(engine)
    _override(vault, engine)
    try:
        resp = TestClient(app).post(
            "/api/cards/card-aaaabbbb/core-change", json={"decision": "full_reset"}
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["core_changed"] is False
    assert body["state"] == "new" and body["stability"] == 0.0 and body["due"] is None


def test_post_core_change_unflagged_is_404(tmp_path: Path):
    vault, engine = _setup(tmp_path)  # no flag set
    _override(vault, engine)
    try:
        resp = TestClient(app).post(
            "/api/cards/card-aaaabbbb/core-change", json={"decision": "keep"}
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_post_core_change_bad_decision_is_422(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _flag(engine)
    _override(vault, engine)
    try:
        resp = TestClient(app).post(
            "/api/cards/card-aaaabbbb/core-change", json={"decision": "obliterate"}
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422  # rejected by the Literal body schema
