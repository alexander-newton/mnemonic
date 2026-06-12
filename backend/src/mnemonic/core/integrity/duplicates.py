"""Detect cards that share an identical normalized core (duplicate candidates)."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DuplicateGroup:
    """A set of cards sharing one normalized core hash.

    Attributes:
        normalized_hash: The shared normalized hash.
        card_ids: The card_ids in the group, sorted.
    """

    normalized_hash: str
    card_ids: list[str]


def find_duplicates(normalized_by_card: Mapping[str, str]) -> list[DuplicateGroup]:
    """Group card_ids by normalized hash, returning only groups with 2+ members.

    Args:
        normalized_by_card: mapping of card_id -> normalized core hash.

    Returns:
        Duplicate groups, ordered by normalized hash, each with sorted card_ids.
        Surfaced as candidates for the user to judge — never auto-merged.
    """
    by_hash: dict[str, list[str]] = {}
    for card_id, normalized in normalized_by_card.items():
        by_hash.setdefault(normalized, []).append(card_id)
    return [
        DuplicateGroup(normalized_hash=h, card_ids=sorted(ids))
        for h, ids in sorted(by_hash.items())
        if len(ids) > 1
    ]
