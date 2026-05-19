"""Session lifecycle: pre-flight → scan → review → commit → push."""

from __future__ import annotations

import logging
from datetime import date
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.exceptions import GitError, GitNonFastForwardError
from mnemonic.vault import git_ops

logger = logging.getLogger(__name__)


class VaultSession:
    def __init__(
        self,
        *,
        vault_root: Path,
        engine: Engine,
        remote: str = "origin",
        branch: str = "main",
    ):
        self.vault_root = vault_root
        self.engine = engine
        self.remote = remote
        self.branch = branch
        self.offline = False
        self._started = False

    # Files/prefixes written by Mnemonic itself; excluded from the user-dirt check.
    _MANAGED_FILES = frozenset([".gitignore", ".gitattributes"])
    _MANAGED_PREFIXES = (".mnemonic/",)

    def start(self) -> None:
        self._ensure_vault_metadata()
        self._assert_user_clean()
        try:
            git_ops.fetch(self.vault_root, self.remote)
        except GitError as e:
            logger.warning("git fetch failed (continuing offline): %s", e)
            self.offline = True
        if not self.offline:
            try:
                git_ops.fast_forward_pull(self.vault_root, self.remote, self.branch)
            except GitNonFastForwardError:
                raise
        self._started = True

    def _assert_user_clean(self) -> None:
        """Raise GitDirtyWorkingTreeError if the user has uncommitted vault changes.

        Ignores Mnemonic-managed files (.gitignore, .gitattributes) which may be
        freshly written by _ensure_vault_metadata.

        Raises:
            GitDirtyWorkingTreeError: If user-owned tracked or untracked files are modified.
            GitError: If the git status command fails.
        """
        from mnemonic.exceptions import GitDirtyWorkingTreeError
        from mnemonic.vault import git_ops as _git_ops

        result = _git_ops._git(self.vault_root, "status", "--porcelain")
        if result.returncode != 0:
            from mnemonic.exceptions import GitError

            raise GitError(f"git status failed: {result.stderr.strip()}")
        dirty_lines = [
            line
            for line in result.stdout.splitlines()
            if line.strip()
            and line[3:].strip() not in self._MANAGED_FILES
            and not any(line[3:].strip().startswith(p) for p in self._MANAGED_PREFIXES)
        ]
        if dirty_lines:
            raise GitDirtyWorkingTreeError(
                f"Vault at {self.vault_root} has uncommitted changes. "
                "Commit or stash them in Obsidian/CLI before starting a Mnemonic session."
            )

    def end(self, *, n_reviews: int, n_variations: int) -> None:
        if not self._started:
            raise RuntimeError("Session must be started before being ended.")
        msg = (
            f"mnemonic: review session {date.today().isoformat()} "
            f"({n_reviews} reviews, {n_variations} variations)"
        )
        sha = git_ops.commit_all(self.vault_root, msg)
        if not sha:
            logger.info("No changes to commit; skipping push.")
            return
        if self.offline:
            logger.warning("Offline: local commit %s retained; will push next session.", sha)
            return
        try:
            git_ops.push(self.vault_root, self.remote, self.branch)
        except GitError as e:
            logger.warning("Push failed: %s. Local commit %s retained.", e, sha)

    def _ensure_vault_metadata(self) -> None:
        """Ensure .mnemonic/ exists and .gitignore/.gitattributes carry Mnemonic-managed lines."""
        (self.vault_root / ".mnemonic").mkdir(exist_ok=True)

        gi_path = self.vault_root / ".gitignore"
        gi_lines = [
            "# managed by mnemonic",
            ".mnemonic/state.sqlite-wal",
            ".mnemonic/state.sqlite-shm",
            ".mnemonic/cache/",
            ".mnemonic/scan.log",
            ".mnemonic/.lock",
        ]
        existing = gi_path.read_text() if gi_path.exists() else ""
        missing = [l for l in gi_lines if l not in existing]
        if missing:
            from mnemonic.vault._atomic import atomic_write_text

            atomic_write_text(
                gi_path,
                (existing.rstrip() + "\n" + "\n".join(missing) + "\n").lstrip("\n"),
            )

        ga_path = self.vault_root / ".gitattributes"
        ga_line = ".mnemonic/state.sqlite binary -diff -merge"
        existing_ga = ga_path.read_text() if ga_path.exists() else ""
        if ga_line not in existing_ga:
            from mnemonic.vault._atomic import atomic_write_text

            atomic_write_text(
                ga_path,
                (existing_ga.rstrip() + "\n" + ga_line + "\n").lstrip("\n"),
            )
