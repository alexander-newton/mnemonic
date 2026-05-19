"""Vault status endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from mnemonic.api.deps import get_config
from mnemonic.exceptions import GitError
from mnemonic.vault import git_ops

router = APIRouter(prefix="/vault", tags=["vault"])


def _head_short(cwd) -> str:
    """Return the short (7-char) SHA of HEAD.

    Args:
        cwd: Working directory path of the git repository.

    Returns:
        Short SHA string.

    Raises:
        GitError: If git rev-parse --short HEAD fails (e.g. not a git repo).
    """
    return git_ops._git_checked(cwd, "rev-parse", "--short", "HEAD").strip()


@router.get("/status")
def vault_status(cfg=Depends(get_config)):
    """Return current vault git status.

    Returns:
        JSON with vault_path, head (short SHA), dirty flag, has_unpushed_commits,
        and branch name.

    Raises:
        HTTPException(503): If any git operation fails (e.g. vault path is not a
            git repository).  Principle #1 — no silent failures.
    """
    cwd = cfg.vault.path
    try:
        head = _head_short(cwd)
        dirty = not git_ops.working_tree_clean(cwd)
        unpushed = git_ops.has_unpushed_commits(
            cwd, branch=cfg.vault.branch
        )
    except (GitError, OSError) as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                f"Vault git error: {exc}. "
                "Check that the vault path is a git repository and the remote is reachable."
            ),
        ) from exc

    return {
        "vault_path": str(cwd),
        "head": head,
        "dirty": dirty,
        "has_unpushed_commits": unpushed,
        "branch": cfg.vault.branch,
    }
