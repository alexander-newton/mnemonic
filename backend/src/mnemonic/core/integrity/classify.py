"""Classify a core edit as new / unchanged / trivial / material / cloze_structure."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ChangeKind = Literal["new", "unchanged", "trivial", "material", "cloze_structure"]


@dataclass(frozen=True)
class StoredHashes:
    """Hashes previously persisted on a card's SchedulingState row (may be None)."""

    core_hash: str | None
    core_hash_normalized: str | None
    cloze_signature: str | None


@dataclass(frozen=True)
class CurrentHashes:
    """Hashes freshly computed from the scanned card body."""

    core_hash: str
    core_hash_normalized: str
    cloze_signature: str | None


@dataclass(frozen=True)
class ChangeVerdict:
    """The classified outcome of comparing stored vs current hashes."""

    kind: ChangeKind


def classify_change(stored: StoredHashes | None, current: CurrentHashes) -> ChangeVerdict:
    """Apply the first-match-wins decision table from the design spec.

    Args:
        stored: Previously persisted hashes, or None for a first-seen card.
        current: Freshly computed hashes for the scanned body.

    Returns:
        A ChangeVerdict whose ``kind`` drives the reconciliation action matrix.
    """
    if stored is None or stored.core_hash is None:
        return ChangeVerdict("new")

    raw_same = stored.core_hash == current.core_hash
    norm_same = stored.core_hash_normalized == current.core_hash_normalized
    cloze_same = stored.cloze_signature == current.cloze_signature

    if raw_same and norm_same and cloze_same:
        return ChangeVerdict("unchanged")
    if norm_same and cloze_same:
        return ChangeVerdict("trivial")
    if not cloze_same:
        return ChangeVerdict("cloze_structure")
    return ChangeVerdict("material")
