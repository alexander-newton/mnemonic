"""Cloze deletion extractor.

Recognises `{{cN::text}}` markers. All clozes (regardless of number) blank
together in the rendered front face — Mnemonic treats one note as one card
per spec §4.2.
"""

from __future__ import annotations

from dataclasses import dataclass

from mnemonic.core.cloze import iter_clozes
from mnemonic.exceptions import InvalidCardSyntaxError


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
    clozes = list(iter_clozes(card_section_text))
    if not clozes:
        raise InvalidCardSyntaxError(
            "Cloze extractor invoked but no {{cN::...}} markers found in card section."
        )

    terms: list[str] = []
    front_parts: list[str] = []
    last_end = 0
    for c in clozes:
        front_parts.append(card_section_text[last_end : c.start])
        front_parts.append("[...]")
        terms.append(c.text)
        last_end = c.end
    front_parts.append(card_section_text[last_end:])
    front = "".join(front_parts).strip()

    return ExtractedCard(
        syntax="cloze", front=front, back=card_section_text.strip(), cloze_terms=terms
    )
