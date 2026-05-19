"""Highlight-cloze extractor.

Recognises `==text==`. All highlights blank together (one note = one card per spec §4.2).
"""

from __future__ import annotations

import re

from mnemonic.exceptions import InvalidCardSyntaxError
from mnemonic.vault.extractors.cloze import ExtractedCard

_HL_RE = re.compile(r"==([^=]+)==")


def extract_highlight(card_section_text: str) -> ExtractedCard:
    matches = list(_HL_RE.finditer(card_section_text))
    if not matches:
        raise InvalidCardSyntaxError(
            "Highlight extractor invoked but no ==text== markers found."
        )

    terms = [m.group(1) for m in matches]

    front_parts: list[str] = []
    last_end = 0
    for m in matches:
        front_parts.append(card_section_text[last_end : m.start()])
        front_parts.append("[...]")
        last_end = m.end()
    front_parts.append(card_section_text[last_end:])

    back_parts: list[str] = []
    last_end = 0
    for m in matches:
        back_parts.append(card_section_text[last_end : m.start()])
        back_parts.append(m.group(1))
        last_end = m.end()
    back_parts.append(card_section_text[last_end:])

    return ExtractedCard(
        syntax="highlight",
        front="".join(front_parts).strip(),
        back="".join(back_parts).strip(),
        cloze_terms=terms,
    )
