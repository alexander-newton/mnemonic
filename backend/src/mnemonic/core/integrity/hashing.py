"""Pure hashing of a card's core (`## Card`) body.

Three signals are derived from one body string:
- raw hash: SHA-256 of the verbatim body (block-ID token excluded) — any change at all.
- normalized hash: SHA-256 of a case/whitespace-folded, de-clozed body — material change.
- cloze signature: hash of the set of (number, answer) cloze pairs — structural change.

Normalization is deliberately conservative (case + whitespace only, no punctuation
stripping) because punctuation is meaningful in math/code cards.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata

from mnemonic.exceptions import IntegrityError

_BLOCK_ID_RE = re.compile(r"\^card-[0-9a-z]+")
_CLOZE_RE = re.compile(r"\{\{c(\d+)::([^}]+)\}\}")
_WHITESPACE_RE = re.compile(r"\s+")


def _strip_block_id(card_body: str) -> str:
    """Remove the ``^card-xxxx`` block-ID token so identity does not affect content hashes."""
    return _BLOCK_ID_RE.sub("", card_body)


def _require_core(card_body: str) -> str:
    """Return the block-ID-stripped, trimmed body, or raise if it is empty."""
    stripped = _strip_block_id(card_body).strip()
    if not stripped:
        raise IntegrityError("Card core body is empty — cannot hash. The note may be malformed.")
    return stripped


def normalize_core(card_body: str) -> str:
    """Case/whitespace-fold a card body and reduce cloze markers to their answer text."""
    nfc = unicodedata.normalize("NFC", _strip_block_id(card_body))
    declozed = _CLOZE_RE.sub(lambda m: m.group(2), nfc)
    folded = declozed.casefold()
    return _WHITESPACE_RE.sub(" ", folded).strip()


def compute_core_hash(card_body: str) -> str:
    """SHA-256 of the verbatim body (block-ID excluded). Raises IntegrityError if empty."""
    return hashlib.sha256(_require_core(card_body).encode("utf-8")).hexdigest()


def compute_normalized_hash(card_body: str) -> str:
    """SHA-256 of the normalized body. Raises IntegrityError if the core is empty."""
    _require_core(card_body)
    return hashlib.sha256(normalize_core(card_body).encode("utf-8")).hexdigest()


def cloze_signature(card_body: str) -> str | None:
    """Hash of the canonical, sorted set of ``(number, answer)`` cloze pairs.

    Returns None when the body contains no cloze markers.
    """
    pairs = _CLOZE_RE.findall(_strip_block_id(card_body))
    if not pairs:
        return None
    canon = "\n".join(f"{num}::{text.strip()}" for num, text in sorted(pairs))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()
