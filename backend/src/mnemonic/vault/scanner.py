"""Vault scanner.

Walks the vault, finds card-notes, extracts cards, optionally injects missing
block IDs. Emits ScannedCard objects (pure data — no SQLite involvement).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from mnemonic.exceptions import InvalidCardSyntaxError, MalformedNoteError
from mnemonic.vault.deck import DeckConfig, resolve_deck_for_note
from mnemonic.vault.extractors import ExtractedCard, extract_card
from mnemonic.vault.injector import inject_block_id
from mnemonic.vault.note import parse_note

logger = logging.getLogger(__name__)

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


def _log_skip(
    note_path: Path,
    vault_root: Path,
    exc: Exception,
    scan_log_path: Path | None,
) -> None:
    """Log a skipped note warning to the module logger and optionally to scan.log.

    Args:
        note_path: Absolute path to the problematic note.
        vault_root: Vault root, used to compute the relative path for the log entry.
        exc: The exception that caused the skip.
        scan_log_path: Path to write the one-line log entry to.  When None, no
            file is written.
    """
    try:
        rel = note_path.relative_to(vault_root)
    except ValueError:
        rel = note_path

    message = f"{type(exc).__name__}: {exc}"
    logger.warning("Skipping malformed note %s — %s", rel, message)

    if scan_log_path is None:
        return
    try:
        scan_log_path.parent.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
        with scan_log_path.open("a", encoding="utf-8") as fh:
            fh.write(f"{timestamp} {rel} {message}\n")
    except OSError as log_err:
        logger.warning("Could not write to scan log %s: %s", scan_log_path, log_err)


def scan_vault(
    vault_root: Path,
    *,
    inject_missing_ids: bool = True,
    scan_log_path: Path | None = None,
) -> Iterator[ScannedCard]:
    """Walk vault and emit ScannedCard objects for every card-note.

    Malformed notes are skipped with a warning logged to the module logger and,
    when ``scan_log_path`` is supplied, appended to that file.  Scanning always
    continues to the next note.

    Args:
        vault_root: Root directory of the vault to scan.
        inject_missing_ids: When True, notes without a block ID have one written
            in place.  When False such notes are skipped.
        scan_log_path: Optional path to append one-line skip entries to.  Defaults
            to ``vault_root / ".mnemonic" / "scan.log"`` when not provided.
    """
    if scan_log_path is None:
        scan_log_path = vault_root / ".mnemonic" / "scan.log"

    for note_path in _iter_notes(vault_root):
        try:
            note = parse_note(note_path.read_text())
        except MalformedNoteError as exc:
            _log_skip(note_path, vault_root, exc, scan_log_path)
            continue

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
        except InvalidCardSyntaxError as exc:
            _log_skip(note_path, vault_root, exc, scan_log_path)
            continue

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
