"""Callout-block extractor.

Recognises Obsidian callouts of the form:

    > [!card]
    > **Q:** ...
    > **A:** ...
"""

from __future__ import annotations

import re

from mnemonic.exceptions import InvalidCardSyntaxError
from mnemonic.vault.extractors.cloze import ExtractedCard

_CALLOUT_OPEN = re.compile(r"^>\s*\[!card\]\s*$", re.MULTILINE)
_BLOCKQUOTE_LINE = re.compile(r"^>\s?(.*)$")


def extract_callout(card_section_text: str) -> ExtractedCard:
    """Parse a card-callout into Q/A."""
    if not _CALLOUT_OPEN.search(card_section_text):
        raise InvalidCardSyntaxError("Callout extractor invoked but no `> [!card]` block found.")

    lines = card_section_text.splitlines()
    inside = False
    body_lines: list[str] = []
    for line in lines:
        if _CALLOUT_OPEN.match(line):
            inside = True
            continue
        if inside:
            m = _BLOCKQUOTE_LINE.match(line)
            if not m:
                break
            body_lines.append(m.group(1))

    body = "\n".join(body_lines).strip()
    q_marker = "**Q:**"
    a_marker = "**A:**"
    if q_marker not in body or a_marker not in body:
        raise InvalidCardSyntaxError(
            "Callout block must contain both **Q:** and **A:** markers."
        )

    q_idx = body.index(q_marker) + len(q_marker)
    a_idx = body.index(a_marker)
    if a_idx < q_idx:
        raise InvalidCardSyntaxError("**A:** must follow **Q:** in a card callout.")

    front = body[q_idx:a_idx].strip()
    back = body[a_idx + len(a_marker) :].strip()

    if not front or not back:
        raise InvalidCardSyntaxError("Callout has empty Q or A.")

    return ExtractedCard(syntax="callout", front=front, back=back, cloze_terms=[])
