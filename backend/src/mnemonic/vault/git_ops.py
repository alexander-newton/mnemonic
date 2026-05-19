"""Subprocess-based Git operations. All raise domain exceptions on failure."""

from __future__ import annotations

import subprocess
from pathlib import Path

from mnemonic.exceptions import (
    GitDirtyWorkingTreeError,
    GitError,
    GitNonFastForwardError,
    GitPushRejectedError,
)


def _git(cwd: Path, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _git_checked(cwd: Path, *args: str) -> str:
    result = _git(cwd, *args)
    if result.returncode != 0:
        raise GitError(
            f"git {' '.join(args)} failed (rc={result.returncode}): {result.stderr.strip()}"
        )
    return result.stdout


def clone(remote: str, dest: Path, branch: str = "main") -> None:
    """Clone a remote repository to dest.

    Args:
        remote: URL or path of the remote repository.
        dest: Local destination path.
        branch: Branch to check out after cloning.

    Raises:
        GitError: If the clone operation fails.
    """
    dest.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["git", "clone", "--branch", branch, remote, str(dest)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise GitError(f"git clone {remote} failed: {result.stderr.strip()}")


def fetch(cwd: Path, remote: str = "origin") -> None:
    """Fetch from a remote.

    Args:
        cwd: Local repository path.
        remote: Remote name to fetch from.

    Raises:
        GitError: If the fetch operation fails.
    """
    result = _git(cwd, "fetch", remote)
    if result.returncode != 0:
        raise GitError(f"git fetch failed: {result.stderr.strip()}")


def working_tree_clean(cwd: Path) -> bool:
    """Return True if the working tree has no uncommitted changes.

    Args:
        cwd: Local repository path.

    Returns:
        True if working tree is clean, False otherwise.

    Raises:
        GitError: If the git status command fails.
    """
    out = _git_checked(cwd, "status", "--porcelain")
    return out.strip() == ""


def assert_clean(cwd: Path) -> None:
    """Raise GitDirtyWorkingTreeError if the working tree is not clean.

    Args:
        cwd: Local repository path.

    Raises:
        GitDirtyWorkingTreeError: If there are uncommitted changes.
        GitError: If the git status command fails.
    """
    if not working_tree_clean(cwd):
        raise GitDirtyWorkingTreeError(
            f"Vault at {cwd} has uncommitted changes. "
            "Commit or stash them in Obsidian/CLI before starting a Mnemonic session."
        )


def is_fast_forward(cwd: Path, ref: str = "origin/main") -> bool:
    """Return True if HEAD is an ancestor of ref (i.e. a fast-forward is possible).

    Args:
        cwd: Local repository path.
        ref: Remote ref to check against.

    Returns:
        True if local HEAD is behind or equal to ref.

    Raises:
        GitError: If rev-parse or merge-base commands fail.
    """
    head = _git_checked(cwd, "rev-parse", "HEAD").strip()
    remote = _git_checked(cwd, "rev-parse", ref).strip()
    if head == remote:
        return True
    merge_base = _git_checked(cwd, "merge-base", head, remote).strip()
    return merge_base == head


def fast_forward_pull(cwd: Path, remote: str = "origin", branch: str = "main") -> None:
    """Pull only if the merge would be fast-forward.

    Args:
        cwd: Local repository path.
        remote: Remote name.
        branch: Branch name.

    Raises:
        GitNonFastForwardError: If the remote has diverged from local.
        GitError: If the merge command fails.
    """
    if not is_fast_forward(cwd, f"{remote}/{branch}"):
        raise GitNonFastForwardError(
            f"Remote {remote}/{branch} has diverged from local. "
            "Reconcile manually in your editor or with `git pull --rebase`."
        )
    result = _git(cwd, "merge", "--ff-only", f"{remote}/{branch}")
    if result.returncode != 0:
        raise GitError(f"fast-forward merge failed: {result.stderr.strip()}")


def commit_all(cwd: Path, message: str) -> str:
    """Stage all changes and create a commit.

    Args:
        cwd: Local repository path.
        message: Commit message.

    Returns:
        The new commit SHA, or empty string if there was nothing to commit.

    Raises:
        GitError: If the commit command fails.
    """
    _git_checked(cwd, "add", "-A")
    status = _git_checked(cwd, "status", "--porcelain")
    if status.strip() == "":
        return ""
    result = _git(cwd, "commit", "-m", message)
    if result.returncode != 0:
        raise GitError(f"git commit failed: {result.stderr.strip()}")
    return _git_checked(cwd, "rev-parse", "HEAD").strip()


def push(cwd: Path, remote: str = "origin", branch: str = "main") -> None:
    """Push local commits to a remote branch.

    Args:
        cwd: Local repository path.
        remote: Remote name.
        branch: Branch name.

    Raises:
        GitPushRejectedError: If the push is rejected due to non-fast-forward.
        GitError: If the push fails for any other reason.
    """
    result = _git(cwd, "push", remote, branch)
    if result.returncode != 0:
        stderr = result.stderr.lower()
        if "rejected" in stderr or "non-fast-forward" in stderr:
            raise GitPushRejectedError(
                f"Push rejected by {remote}/{branch}: remote has newer commits. "
                "Run a fresh Mnemonic session or `git pull` to reconcile."
            )
        raise GitError(f"git push failed: {result.stderr.strip()}")


def has_unpushed_commits(cwd: Path, remote: str = "origin", branch: str = "main") -> bool:
    """Return True if there are local commits not yet on the remote.

    Args:
        cwd: Local repository path.
        remote: Remote name.
        branch: Branch name.

    Returns:
        True if there are unpushed commits.

    Raises:
        GitError: If the git log command fails.
    """
    out = _git_checked(cwd, "log", f"{remote}/{branch}..HEAD", "--oneline")
    return out.strip() != ""
