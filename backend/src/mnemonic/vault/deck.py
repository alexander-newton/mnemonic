"""Deck resolution: folder = deck. Optional `_deck.md` provides per-folder config."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from mnemonic.exceptions import MalformedNoteError

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)


@dataclass(frozen=True)
class DeckConfig:
    deck_name: str
    variation_enabled: bool
    variation_frequency: float
    leech_threshold: int
    daily_review_limit: int
    daily_new_limit: int


def parse_deck_config(deck_md_path: Path) -> DeckConfig:
    """Parse a `_deck.md` file's frontmatter into a DeckConfig."""
    text = deck_md_path.read_text()
    m = _FRONTMATTER_RE.match(text)
    if not m:
        raise MalformedNoteError(f"{deck_md_path} has no YAML frontmatter.")
    fm = yaml.safe_load(m.group(1)) or {}
    required = (
        "deck_name",
        "variation_enabled",
        "variation_frequency",
        "leech_threshold",
        "daily_review_limit",
        "daily_new_limit",
    )
    missing = [k for k in required if k not in fm]
    if missing:
        raise MalformedNoteError(
            f"{deck_md_path} _deck.md missing required keys: {missing}."
        )
    return DeckConfig(
        deck_name=str(fm["deck_name"]),
        variation_enabled=bool(fm["variation_enabled"]),
        variation_frequency=float(fm["variation_frequency"]),
        leech_threshold=int(fm["leech_threshold"]),
        daily_review_limit=int(fm["daily_review_limit"]),
        daily_new_limit=int(fm["daily_new_limit"]),
    )


def resolve_deck_for_note(
    note_path: Path, *, vault_root: Path
) -> tuple[Path, DeckConfig | None]:
    """Return (deck_folder, deck_config_or_None_if_no_deck.md_in_chain).

    Walks upward from the note's folder until vault_root, returning the first
    `_deck.md` config found. Deck folder is always the note's immediate parent.
    """
    deck_folder = note_path.parent
    cur = deck_folder
    while True:
        candidate = cur / "_deck.md"
        if candidate.exists():
            return (deck_folder, parse_deck_config(candidate))
        if cur == vault_root or cur.parent == cur:
            return (deck_folder, None)
        cur = cur.parent
