import re
from pathlib import Path
import pytest
from mnemonic.vault.injector import inject_block_id, ensure_variations_section, append_variation_entry
from mnemonic.vault.note import BLOCK_ID_RE
from mnemonic.exceptions import MalformedNoteError, MalformedVariationSectionError


def _read(p: Path) -> str:
    return p.read_text()


def test_inject_block_id_appends_to_card_paragraph(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA {{c1::NE}} is stable.\n\n## Context\n\nfoo\n"
    )
    cid = inject_block_id(note)
    text = _read(note)
    assert BLOCK_ID_RE.search(text)
    assert cid.startswith("card-")
    assert len(cid) == len("card-") + 8


def test_inject_block_id_idempotent_when_already_present(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA ==NE== is stable. ^card-aaaabbbb\n"
    )
    cid = inject_block_id(note)
    assert cid == "card-aaaabbbb"
    assert _read(note).count("^card-aaaabbbb") == 1


def test_inject_raises_when_no_card_section(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text("---\ntitle: t\n---\n\nno card here\n")
    with pytest.raises(MalformedNoteError):
        inject_block_id(note)


def test_ensure_variations_section_creates_when_absent(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA ==NE==. ^card-aaaabbbb\n"
    )
    ensure_variations_section(note)
    text = _read(note)
    assert "## Variations" in text
    assert "<!-- mnemonic:variations:begin -->" in text
    assert "<!-- mnemonic:variations:end -->" in text


def test_append_variation_entry_inserts_before_end_marker(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA ==NE==. ^card-aaaabbbb\n\n"
        "## Variations\n\n<!-- mnemonic:variations:begin -->\n<!-- mnemonic:variations:end -->\n"
    )
    append_variation_entry(
        note,
        date_str="2026-05-10",
        question="When is X?",
        answer="When Y.",
    )
    text = _read(note)
    assert "### 2026-05-10 (rating: pending)" in text
    assert text.index("### 2026-05-10") < text.index("<!-- mnemonic:variations:end -->")


def test_append_variation_entry_raises_if_markers_missing(tmp_path: Path):
    note = tmp_path / "n.qmd"
    note.write_text(
        "---\ntitle: t\n---\n\n## Card\n\nA. ^card-aaaabbbb\n\n## Variations\n\n### 2026-04-01\nfoo\n"
    )
    with pytest.raises(MalformedVariationSectionError):
        append_variation_entry(note, "2026-05-10", "q", "a")
