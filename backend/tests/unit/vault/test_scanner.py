from pathlib import Path
from mnemonic.vault.scanner import scan_vault, ScannedCard


def _make_note(p: Path, body: str) -> None:
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(body)


def test_scan_emits_one_card_per_card_note(tmp_path: Path):
    vault = tmp_path / "vault"
    _make_note(
        vault / "01_Projects" / "game-theory" / "nash.qmd",
        "---\ntitle: nash\n---\n## Card\n\nA {{c1::NE}} is stable. ^card-11112222\n",
    )
    _make_note(
        vault / "01_Projects" / "game-theory" / "minimax.qmd",
        "---\ntitle: minimax\n---\n## Card\n\nA ==minimax==. ^card-33334444\n",
    )
    cards = list(scan_vault(vault))
    assert len(cards) == 2
    ids = {c.card_id for c in cards}
    assert ids == {"card-11112222", "card-33334444"}
    syntaxes = {c.syntax for c in cards}
    assert syntaxes == {"cloze", "highlight"}


def test_scan_skips_non_card_notes(tmp_path: Path):
    vault = tmp_path / "vault"
    _make_note(vault / "01_Projects" / "regular-note.md", "no card section here")
    cards = list(scan_vault(vault))
    assert cards == []


def test_scan_injects_block_ids_when_missing(tmp_path: Path):
    vault = tmp_path / "vault"
    note = vault / "01_Projects" / "no-id.qmd"
    _make_note(note, "---\ntitle: x\n---\n## Card\n\nA ==NE==.\n")
    cards = list(scan_vault(vault, inject_missing_ids=True))
    assert len(cards) == 1
    assert cards[0].card_id.startswith("card-")
    assert "^card-" in note.read_text()


def test_scan_skips_mnemonic_folder(tmp_path: Path):
    vault = tmp_path / "vault"
    _make_note(vault / ".mnemonic" / "should-not-scan.md", "## Card\n\nA ==X==.")
    cards = list(scan_vault(vault, inject_missing_ids=False))
    assert cards == []


def test_scan_skips_malformed_note_and_logs(tmp_path: Path):
    """A malformed note must be skipped (not halt), and logged to scan.log."""
    vault = tmp_path / "vault"
    # Valid note
    _make_note(
        vault / "valid.qmd",
        "---\ntitle: valid\n---\n## Card\n\nA ==term==. ^card-aaaabbbb\n",
    )
    # Malformed note: has ## Card and title but ## Variations section is missing markers
    _make_note(
        vault / "bad.qmd",
        "---\ntitle: bad\n---\n"
        "## Card\n\nA ==term==. ^card-ccccdddd\n\n"
        "## Variations\n\nsome content without markers\n",
    )
    scan_log = vault / ".mnemonic" / "scan.log"
    cards = list(scan_vault(vault, scan_log_path=scan_log))
    # Only the valid card comes through
    assert len(cards) == 1
    assert cards[0].card_id == "card-aaaabbbb"
    # The scan log must exist and mention bad.qmd
    assert scan_log.exists()
    log_text = scan_log.read_text()
    assert "bad.qmd" in log_text
