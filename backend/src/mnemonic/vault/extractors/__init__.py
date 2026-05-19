"""Card-marker extractors. Each module exposes an `extract_*` function returning ExtractedCard."""

from mnemonic.vault.extractors.cloze import ExtractedCard, extract_cloze

__all__ = ["ExtractedCard", "extract_cloze"]
