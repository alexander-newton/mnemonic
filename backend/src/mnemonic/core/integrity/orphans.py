"""Detect references that point at cards no longer present in the vault."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass


@dataclass(frozen=True)
class DanglingRefs:
    """Buckets of references whose target card is no longer live.

    Attributes:
        review_logs: card_ids referenced by review logs but absent from the vault.
        variations: card_ids with variation metadata but absent from the vault.
        parents: child card_ids whose ``parent_card_id`` is absent from the vault.
    """

    review_logs: list[str]
    variations: list[str]
    parents: list[str]


def find_dangling_refs(
    live_card_ids: set[str],
    review_card_ids: Iterable[str],
    variation_card_ids: Iterable[str],
    parent_links: Mapping[str, str | None],
) -> DanglingRefs:
    """Compute the three dangling-reference buckets.

    Args:
        live_card_ids: card_ids present in the current vault scan.
        review_card_ids: card_ids referenced by ReviewLog rows.
        variation_card_ids: card_ids referenced by VariationMeta rows.
        parent_links: mapping of child card_id -> its parent_card_id.

    Returns:
        A DanglingRefs with each bucket sorted and de-duplicated.
    """
    review = sorted({cid for cid in review_card_ids if cid not in live_card_ids})
    variations = sorted({cid for cid in variation_card_ids if cid not in live_card_ids})
    parents = sorted(
        {child for child, parent in parent_links.items() if parent and parent not in live_card_ids}
    )
    return DanglingRefs(review_logs=review, variations=variations, parents=parents)
