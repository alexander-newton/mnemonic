"""Vault scanner.

Walks the vault, finds card-notes, extracts cards, optionally injects missing
block IDs. Emits ScannedCard objects (pure data — no SQLite involvement).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

from mnemonic.exceptions import InvalidCardSyntaxError, MalformedNoteError
from mnemonic.vault.deck import DeckConfig, resolve_deck_for_note
from mnemonic.vault.extractors import ExtractedCard, extract_card
from mnemonic.vault.injector import inject_block_id
from mnemonic.vault.note import parse_note

NOTE_SUFFIXES = (".md", ".qmd")
SKIP_DIRS = {".mnemonic", ".obsidian", ".git", "_build", "node_modules"}


@dataclass(frozen=True)
class ScannedCard:
    card_id: str
    note_path: Path
    deck_folder: Path
    deck_config: DeckConfig | None
    syntax: str
    front: str
    back: str
    title: str
    frontmatter: dict


def _iter_notes(vault_root: Path) -> Iterator[Path]:
    for path in vault_root.rglob("*"):
        if path.is_dir():
            continue
        if path.suffix not in NOTE_SUFFIXES:
            continue
        rel = path.relative_to(vault_root)
        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if path.name.startswith("_deck"):
            continue
        yield path


def scan_vault(
    vault_root: Path, *, inject_missing_ids: bool = True
) -> Iterator[ScannedCard]:
    """Walk vault and emit ScannedCard objects for every card-note."""
    for note_path in _iter_notes(vault_root):
        try:
            note = parse_note(note_path.read_text())
        except MalformedNoteError:
            raise
        if not note.is_card_note:
            continue

        if note.block_id is None:
            if not inject_missing_ids:
                continue
            block_id = inject_block_id(note_path)
            note = parse_note(note_path.read_text())
        else:
            block_id = note.block_id

        try:
            extracted: ExtractedCard = extract_card(note.card_section or "")
        except InvalidCardSyntaxError:
            raise

        deck_folder, deck_cfg = resolve_deck_for_note(note_path, vault_root=vault_root)

        yield ScannedCard(
            card_id=block_id,
            note_path=note_path,
            deck_folder=deck_folder,
            deck_config=deck_cfg,
            syntax=extracted.syntax,
            front=extracted.front,
            back=extracted.back,
            title=str(note.frontmatter.get("title", "")),
            frontmatter=note.frontmatter,
        )
