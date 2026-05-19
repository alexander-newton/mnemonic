import subprocess
from pathlib import Path
import pytest
from mnemonic.db.models import Base, ReviewLog
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.vault.session import VaultSession
from mnemonic.exceptions import GitDirtyWorkingTreeError


def _run(cmd, cwd):
    subprocess.run(cmd, cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _run(["git", "init", "--bare", "--initial-branch=main"], bare)
    local = tmp_path / "vault"
    local.mkdir()
    _run(["git", "init", "--initial-branch=main"], local)
    _run(["git", "config", "user.email", "t@t.t"], local)
    _run(["git", "config", "user.name", "t"], local)
    _run(["git", "remote", "add", "origin", str(bare)], local)
    (local / "01_Projects" / "gt").mkdir(parents=True)
    (local / "01_Projects" / "gt" / "nash.qmd").write_text(
        "---\ntitle: nash\n---\n## Card\n\nA ==NE==.\n"
    )
    (local / ".gitattributes").write_text(".mnemonic/state.sqlite binary -diff -merge\n")
    _run(["git", "add", "."], local)
    _run(["git", "commit", "-m", "init"], local)
    _run(["git", "push", "-u", "origin", "main"], local)
    return local


def test_session_completes_and_commits(repo: Path):
    engine = create_engine(repo / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    sess = VaultSession(vault_root=repo, engine=engine)
    sess.start()
    sess.end(n_reviews=1, n_variations=0)
    log = subprocess.check_output(["git", "log", "--oneline"], cwd=repo).decode()
    assert "mnemonic: review session" in log


def test_session_refuses_on_dirty_tree(repo: Path):
    (repo / "01_Projects" / "gt" / "extra.md").write_text("untracked")
    engine = create_engine(repo / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    sess = VaultSession(vault_root=repo, engine=engine)
    with pytest.raises(GitDirtyWorkingTreeError):
        sess.start()
