import subprocess
from pathlib import Path
import pytest
from mnemonic.vault import git_ops
from mnemonic.exceptions import GitDirtyWorkingTreeError, GitNonFastForwardError


def _run(cmd: list[str], cwd: Path) -> None:
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare", "--initial-branch=main"], bare)

    local = tmp_path / "local"
    local.mkdir()
    _run(["git", "init", "--initial-branch=main"], local)
    _run(["git", "config", "user.email", "t@t.t"], local)
    _run(["git", "config", "user.name", "t"], local)
    _run(["git", "remote", "add", "origin", str(bare)], local)
    (local / "x.md").write_text("hello")
    _run(["git", "add", "."], local)
    _run(["git", "commit", "-m", "init"], local)
    _run(["git", "push", "-u", "origin", "main"], local)
    return local


def test_working_tree_clean(repo: Path):
    assert git_ops.working_tree_clean(repo) is True
    (repo / "x.md").write_text("modified")
    assert git_ops.working_tree_clean(repo) is False


def test_commit_all_and_push(repo: Path):
    (repo / "new.md").write_text("new")
    sha = git_ops.commit_all(repo, "test commit")
    assert sha
    git_ops.push(repo)


def test_dirty_tree_raises_on_session_preflight(repo: Path):
    (repo / "x.md").write_text("dirty")
    with pytest.raises(GitDirtyWorkingTreeError):
        git_ops.assert_clean(repo)
