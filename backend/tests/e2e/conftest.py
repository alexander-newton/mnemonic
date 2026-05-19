import subprocess
from pathlib import Path
import pytest


def _git(cwd, *args):
    subprocess.run(["git", *args], cwd=cwd, check=True, capture_output=True)


@pytest.fixture
def fixture_vault(tmp_path: Path):
    bare = tmp_path / "remote.git"
    bare.mkdir()
    _git(bare, "init", "--bare", "--initial-branch=main")

    vault = tmp_path / "vault"
    vault.mkdir()
    _git(vault, "init", "--initial-branch=main")
    _git(vault, "config", "user.email", "t@t.t")
    _git(vault, "config", "user.name", "t")
    _git(vault, "remote", "add", "origin", str(bare))

    folder = vault / "01_Projects" / "game-theory"
    folder.mkdir(parents=True)
    src = Path(__file__).parent.parent / "llm" / "golden" / "nash-equilibrium.qmd"
    (folder / "nash.qmd").write_text(src.read_text())

    (vault / ".gitattributes").write_text(".mnemonic/state.sqlite binary -diff -merge\n")
    _git(vault, "add", ".")
    _git(vault, "commit", "-m", "init")
    _git(vault, "push", "-u", "origin", "main")
    return vault
