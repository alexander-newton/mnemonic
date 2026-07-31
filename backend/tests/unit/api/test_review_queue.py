"""Tests for GET /api/reviews/queue."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mnemonic.api.deps import get_queue_service
from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.main import app
from mnemonic.services.review_queue import QueueService
from mnemonic.vault.repository import VaultRepository


def _setup(tmp_path: Path):
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
    return vault, engine


def _override(vault, engine):
    app.dependency_overrides[get_queue_service] = lambda: QueueService(
        repo=VaultRepository(vault_root=vault, engine=engine),
        engine=engine,
        default_new_per_day=20,
        default_due_per_day=200,
    )


def test_queue_returns_items(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert len(body["cards"]) == 1
    assert body["cards"][0]["card_id"] == "card-aaaabbbb"
    assert body["cards"][0]["front"] == "A [...] equilibrium."
    assert body["cards"][0]["answer"] == "A **Nash** equilibrium."
    assert set(body["cards"][0]["previews"].keys()) == {"1", "2", "3", "4"}
    assert body["limits"] == {"minutes_per_session": None}


def test_queue_unknown_deck_404(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=nope")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 404


def test_queue_malformed_policy_returns_422(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text('[[rule]]\norder = "sideways"\n')
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert "order" in resp.json()["detail"]


def test_queue_surfaces_minutes_per_session(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    (vault / ".mnemonic").mkdir(parents=True, exist_ok=True)
    (vault / ".mnemonic" / "policy.toml").write_text("[[rule]]\nminutes_per_session = 30\n")
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json()["limits"]["minutes_per_session"] == 30


def test_queue_serializes_variation_fields_as_null_when_absent(tmp_path: Path):
    vault, engine = _setup(tmp_path)
    _override(vault, engine)
    try:
        resp = TestClient(app).get("/api/reviews/queue?deck=gt")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    card = resp.json()["cards"][0]
    assert card["variation_id"] is None
    assert card["variation_front"] is None
    assert card["variation_answer"] is None
