"""Parser for the canonical Mnemonic note structure.

A card-note has:
  - YAML frontmatter (title required)
  - ## Card section (contains card markers + optional ^card-xyz block ID)
  - ## Context section (optional)
  - ## Variations section (optional; bounded by mnemonic markers)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

import yaml

from mnemonic.exceptions import MalformedNoteError

BLOCK_ID_RE = re.compile(r"\^(card-[0-9a-f]+)\b")
VAR_BEGIN = "<!-- mnemonic:variations:begin -->"
VAR_END = "<!-- mnemonic:variations:end -->"

_FRONTMATTER_RE = re.compile(r"\A---\n(.*?)\n---\n", re.DOTALL)
_HEADING_RE = re.compile(r"^##\s+(\S.*?)\s*$", re.MULTILINE)


@dataclass(frozen=True)
class ParsedNote:
    frontmatter: dict[str, Any]
    card_section: str | None
    context_section: str | None
    variations_section: str | None
    block_id: str | None
    raw_text: str

    @property
    def is_card_note(self) -> bool:
        return self.card_section is not None


def parse_note(text: str) -> ParsedNote:
    """Parse a Mnemonic note. Raises MalformedNoteError on structural problems."""
    frontmatter, body = _split_frontmatter(text)

    sections = _split_h2_sections(body)
    card = sections.get("Card")
    context = sections.get("Context")
    variations = sections.get("Variations")

    if card is None:
        return ParsedNote(
            frontmatter=frontmatter,
            card_section=None,
            context_section=None,
            variations_section=None,
            block_id=None,
            raw_text=text,
        )

    if "title" not in frontmatter:
        raise MalformedNoteError(
            "Card-note missing required `title` field in frontmatter."
        )

    if variations is not None:
        if VAR_BEGIN not in variations or VAR_END not in variations:
            raise MalformedNoteError(
                "## Variations section is missing the mnemonic markers. "
                f"Expected `{VAR_BEGIN}` and `{VAR_END}`."
            )

    block_id_match = BLOCK_ID_RE.search(card)
    block_id = block_id_match.group(1) if block_id_match else None

    return ParsedNote(
        frontmatter=frontmatter,
        card_section=card,
        context_section=context,
        variations_section=variations,
        block_id=block_id,
        raw_text=text,
    )


def _split_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return ({}, text)
    try:
        fm = yaml.safe_load(m.group(1)) or {}
    except yaml.YAMLError as e:
        raise MalformedNoteError(f"Invalid YAML in frontmatter: {e}") from e
    if not isinstance(fm, dict):
        raise MalformedNoteError("Frontmatter must be a YAML mapping.")
    return (fm, text[m.end() :])


def _split_h2_sections(body: str) -> dict[str, str]:
    """Return a dict mapping each ## heading text to the body following it."""
    matches = list(_HEADING_RE.finditer(body))
    out: dict[str, str] = {}
    for i, m in enumerate(matches):
        name = m.group(1).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        out[name] = body[start:end].strip("\n")
    return out
