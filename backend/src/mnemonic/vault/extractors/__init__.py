"""Card-marker extractors with syntax auto-detection."""

from __future__ import annotations

import re

from mnemonic.exceptions import InvalidCardSyntaxError
from mnemonic.vault.extractors.callout import extract_callout
from mnemonic.vault.extractors.cloze import ExtractedCard, extract_cloze
from mnemonic.vault.extractors.highlight import extract_highlight

__all__ = ["ExtractedCard", "extract_card", "extract_cloze", "extract_highlight", "extract_callout"]

_CLOZE_HINT = re.compile(r"\{\{c\d+::")
_HIGHLIGHT_HINT = re.compile(r"==[^=]+==")
_CALLOUT_HINT = re.compile(r"^>\s*\[!card\]", re.MULTILINE)


def extract_card(card_section_text: str) -> ExtractedCard:
    """Detect which syntax is used and dispatch to the correct extractor.

    Raises InvalidCardSyntaxError if zero or more than one syntax is present.
    """
    has_cloze = bool(_CLOZE_HINT.search(card_section_text))
    has_hl = bool(_HIGHLIGHT_HINT.search(card_section_text))
    has_callout = bool(_CALLOUT_HINT.search(card_section_text))

    syntaxes = sum([has_cloze, has_hl, has_callout])
    if syntaxes == 0:
        raise InvalidCardSyntaxError(
            "No supported card syntax detected. Use {{cN::...}}, ==text==, or > [!card]."
        )
    if syntaxes > 1:
        present = [n for n, p in (("cloze", has_cloze), ("highlight", has_hl), ("callout", has_callout)) if p]
        raise InvalidCardSyntaxError(
            f"Mixed card syntaxes in one note: {present}. A note must use exactly one."
        )

    if has_cloze:
        return extract_cloze(card_section_text)
    if has_hl:
        return extract_highlight(card_section_text)
    return extract_callout(card_section_text)
