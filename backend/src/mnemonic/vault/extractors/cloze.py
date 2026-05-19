"""Cloze deletion extractor.

Recognises `{{cN::text}}` markers. All clozes (regardless of number) blank
together in the rendered front face — Mnemonic treats one note as one card
per spec §4.2.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mnemonic.exceptions import InvalidCardSyntaxError

_CLOZE_RE = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")


@dataclass(frozen=True)
class ExtractedCard:
    syntax: str  # "cloze" | "highlight" | "callout"
    front: str
    back: str
    cloze_terms: list[str]


def extract_cloze(card_section_text: str) -> ExtractedCard:
    """Parse a `## Card` body containing cloze markers.

    Raises InvalidCardSyntaxError if no marker found.
    """
    matches = list(_CLOZE_RE.finditer(card_section_text))
    if not matches:
        raise InvalidCardSyntaxError(
            "Cloze extractor invoked but no {{cN::...}} markers found in card section."
        )

    terms: list[str] = []
    front_parts: list[str] = []
    last_end = 0
    for m in matches:
        front_parts.append(card_section_text[last_end : m.start()])
        front_parts.append("[...]")
        terms.append(m.group(2))
        last_end = m.end()
    front_parts.append(card_section_text[last_end:])
    front = "".join(front_parts).strip()

    return ExtractedCard(syntax="cloze", front=front, back=card_section_text.strip(), cloze_terms=terms)
