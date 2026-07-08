"""Tests for POST /api/vault/reconcile."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from mnemonic.api.deps import get_reconciliation_service
from mnemonic.db.models import Base
from mnemonic.db.sqlite import create_engine
from mnemonic.exceptions import IntegrityError
from mnemonic.main import app
from mnemonic.services.reconciliation import ReconciliationService


def _vault(tmp_path: Path):
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    (vault / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nThe {{c1::Nash}} equilibrium.\n"
    )
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return vault, engine


def test_reconcile_returns_full_report(tmp_path: Path):
    vault, engine = _vault(tmp_path)
    app.dependency_overrides[get_reconciliation_service] = lambda: ReconciliationService(
        vault_root=vault, engine=engine
    )
    try:
        resp = TestClient(app).post("/api/vault/reconcile")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    body = resp.json()
    assert body["counts"]["new"] == 1
    assert body["dangling"] == {"review_logs": [], "variations": [], "parents": []}
    assert body["duplicates"] == []


def test_reconcile_surfaces_integrity_error_as_422():
    class _Boom:
        def run(self):
            raise IntegrityError("Card card-x in /v/broken.qmd has an empty core body.")

    app.dependency_overrides[get_reconciliation_service] = lambda: _Boom()
    try:
        resp = TestClient(app).post("/api/vault/reconcile")
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 422
    assert "empty core body" in resp.json()["detail"]
