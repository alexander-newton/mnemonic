"""Integration tests for the /api/vault/status endpoint."""

from __future__ import annotations

import subprocess
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from mnemonic.api.deps import get_config as _original_get_config
from mnemonic.main import app


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture()
def git_vault(tmp_path: Path) -> Path:
    """A minimal initialised git repository acting as a vault."""
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare", "--initial-branch=main"], bare)

    local = tmp_path / "vault"
    local.mkdir()
    _run(["git", "init", "--initial-branch=main"], local)
    _run(["git", "config", "user.email", "t@t.t"], local)
    _run(["git", "config", "user.name", "t"], local)
    _run(["git", "remote", "add", "origin", str(bare)], local)
    (local / "note.md").write_text("hello")
    _run(["git", "add", "."], local)
    _run(["git", "commit", "-m", "init"], local)
    _run(["git", "push", "-u", "origin", "main"], local)
    return local


def _make_config(vault_path: Path, branch: str = "main"):
    """Build a minimal Config object pointing at the given vault path."""
    from mnemonic.config import (
        BudgetConfig,
        Config,
        DefaultsConfig,
        LLMConfig,
        VaultConfig,
    )

    return Config(
        vault=VaultConfig(
            path=vault_path,
            remote=None,
            branch=branch,
            watch=False,
        ),
        llm=LLMConfig(
            api_key_env="ANTHROPIC_API_KEY",
            model_default="claude-haiku-4-5",
            model_rephrase="claude-haiku-4-5",
            model_offline="claude-haiku-4-5",
            budget=BudgetConfig(daily_cents=100, monthly_cents=1000),
        ),
        defaults=DefaultsConfig(
            variation_enabled=False,
            variation_frequency=0.5,
            leech_threshold=8,
            daily_review_limit=100,
            daily_new_limit=20,
        ),
    )


class TestVaultStatusHappyPath:
    def test_returns_200_with_head_sha_and_correct_flags(self, git_vault: Path):
        """A clean vault with no unpushed commits must return 200, a short SHA,
        dirty=False, and has_unpushed_commits=False."""
        cfg = _make_config(git_vault)
        # Override the FastAPI dependency directly so lru_cache is not an issue
        app.dependency_overrides[_original_get_config] = lambda: cfg
        try:
            client = TestClient(app)
            resp = client.get("/api/vault/status")
        finally:
            app.dependency_overrides.pop(_original_get_config, None)

        assert resp.status_code == 200
        data = resp.json()
        assert len(data["head"]) == 7  # short SHA is 7 chars
        assert data["dirty"] is False
        assert data["has_unpushed_commits"] is False
        assert data["branch"] == "main"
        assert str(git_vault) in data["vault_path"]


class TestVaultStatusErrorPath:
    def test_nonexistent_vault_path_returns_503(self, tmp_path: Path):
        """A vault path that is not a git repo must return 503, not a silent 200
        with empty strings — Principle #1: no silent failures."""
        cfg = _make_config(tmp_path / "no-such-repo")
        app.dependency_overrides[_original_get_config] = lambda: cfg
        try:
            client = TestClient(app, raise_server_exceptions=False)
            resp = client.get("/api/vault/status")
        finally:
            app.dependency_overrides.pop(_original_get_config, None)

        assert resp.status_code == 503
        body = resp.json()
        assert "detail" in body
        # The error message must contain something actionable, not be empty
        assert body["detail"]
