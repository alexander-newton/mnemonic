"""Mnemonic-managed writes to vault notes.

Operations:
  - inject_block_id(note_path) → str: append ^card-xyz at end of `## Card` if missing.
  - ensure_variations_section(note_path): add an empty ## Variations stub.
  - append_variation_entry(note_path, date, q, a): insert a pending entry before :end marker.
  - update_variation_rating(note_path, date, rating): "(rating: pending)" → "(rating: N)".

All writes atomic via _atomic.atomic_write_text.
"""

from __future__ import annotations

import re
import secrets
from pathlib import Path

from mnemonic.exceptions import MalformedNoteError, MalformedVariationSectionError
from mnemonic.vault._atomic import atomic_write_text
from mnemonic.vault.note import BLOCK_ID_RE, VAR_BEGIN, VAR_END, parse_note


def _new_block_id() -> str:
    """Generate a new unique block ID."""
    return f"card-{secrets.token_hex(4)}"


def inject_block_id(note_path: Path) -> str:
    """Append a block ID to the `## Card` section if missing. Returns the ID.

    Args:
        note_path: Path to the note file.

    Returns:
        The block ID (either newly generated or existing).

    Raises:
        MalformedNoteError: If the note has no ## Card section or Card section is empty.
    """
    text = note_path.read_text()
    note = parse_note(text)
    if note.card_section is None:
        raise MalformedNoteError(
            f"Cannot inject block ID: {note_path} has no ## Card section."
        )
    if note.block_id is not None:
        return note.block_id

    card_section = note.card_section
    new_block_id = _new_block_id()
    lines = card_section.splitlines()
    last_nonblank = next((i for i in range(len(lines) - 1, -1, -1) if lines[i].strip()), None)
    if last_nonblank is None:
        raise MalformedNoteError("## Card section is empty.")
    lines[last_nonblank] = lines[last_nonblank].rstrip() + f" ^{new_block_id}"
    new_card = "\n".join(lines)

    new_text = text.replace(card_section, new_card, 1)
    atomic_write_text(note_path, new_text)
    return new_block_id


def ensure_variations_section(note_path: Path) -> None:
    """Append an empty `## Variations` section with markers if not present.

    Args:
        note_path: Path to the note file.

    Raises:
        MalformedVariationSectionError: If ## Variations exists but is missing markers.
    """
    text = note_path.read_text()
    note = parse_note(text)
    if note.variations_section is not None:
        if VAR_BEGIN not in note.variations_section or VAR_END not in note.variations_section:
            raise MalformedVariationSectionError(
                f"## Variations section in {note_path} is missing markers."
            )
        return
    new_block = (
        "\n## Variations\n\n"
        f"{VAR_BEGIN}\n"
        f"{VAR_END}\n"
    )
    new_text = text.rstrip() + "\n" + new_block
    atomic_write_text(note_path, new_text)


def append_variation_entry(
    note_path: Path, date_str: str, question: str, answer: str
) -> None:
    """Insert a pending variation entry before the :end marker.

    Args:
        note_path: Path to the note file.
        date_str: Date string for the variation (e.g., "2026-05-10").
        question: The generated question.
        answer: The generated answer.

    Raises:
        MalformedVariationSectionError: If ## Variations markers are missing.
    """
    text = note_path.read_text()
    if VAR_BEGIN not in text or VAR_END not in text:
        raise MalformedVariationSectionError(
            f"{note_path} has no ## Variations markers; call ensure_variations_section first."
        )
    entry = (
        f"### {date_str} (rating: pending)\n"
        f"**Q:** {question}\n"
        f"**A:** {answer}\n\n"
    )
    new_text = text.replace(VAR_END, entry + VAR_END, 1)
    atomic_write_text(note_path, new_text)


def update_variation_rating(note_path: Path, date_str: str, rating: int) -> None:
    """Change the most recent `(rating: pending)` entry for date_str to (rating: N).

    Args:
        note_path: Path to the note file.
        date_str: The date string to match (e.g., "2026-05-10").
        rating: The numeric rating (1-4).

    Raises:
        MalformedVariationSectionError: If no pending entry found for the date.
    """
    text = note_path.read_text()
    pat = re.compile(rf"### {re.escape(date_str)} \(rating: pending\)")
    new_text, count = pat.subn(f"### {date_str} (rating: {rating})", text, count=1)
    if count == 0:
        raise MalformedVariationSectionError(
            f"No pending entry found for {date_str} in {note_path}."
        )
    atomic_write_text(note_path, new_text)
