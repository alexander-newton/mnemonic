"""Vault status endpoint."""

from __future__ import annotations

import subprocess

from fastapi import APIRouter, Depends

from mnemonic.api.deps import get_config

router = APIRouter(prefix="/vault", tags=["vault"])


def _git_out(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


@router.get("/status")
def vault_status(cfg=Depends(get_config)):
    cwd = cfg.vault.path
    head = _git_out(cwd, "rev-parse", "--short", "HEAD")
    dirty = _git_out(cwd, "status", "--porcelain") != ""
    unpushed = _git_out(cwd, "log", "origin/main..HEAD", "--oneline") != ""
    return {
        "vault_path": str(cwd),
        "head": head,
        "dirty": dirty,
        "has_unpushed_commits": unpushed,
        "branch": cfg.vault.branch,
    }
