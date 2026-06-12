"""Tests for dangling-reference detection."""

from __future__ import annotations

from mnemonic.core.integrity.orphans import find_dangling_refs


def test_no_dangling_when_all_refs_live():
    live = {"a", "b"}
    refs = find_dangling_refs(
        live_card_ids=live,
        review_card_ids={"a", "b"},
        variation_card_ids={"a"},
        parent_links={"b": "a"},
    )
    assert refs.review_logs == []
    assert refs.variations == []
    assert refs.parents == []


def test_dangling_review_log():
    refs = find_dangling_refs(
        live_card_ids={"a"},
        review_card_ids={"a", "gone"},
        variation_card_ids=set(),
        parent_links={},
    )
    assert refs.review_logs == ["gone"]


def test_dangling_variation():
    refs = find_dangling_refs(
        live_card_ids={"a"},
        review_card_ids=set(),
        variation_card_ids={"gone"},
        parent_links={},
    )
    assert refs.variations == ["gone"]


def test_dangling_parent_link_reports_child():
    # child "c" points at a parent that no longer exists
    refs = find_dangling_refs(
        live_card_ids={"c"},
        review_card_ids=set(),
        variation_card_ids=set(),
        parent_links={"c": "deadparent"},
    )
    assert refs.parents == ["c"]


def test_results_are_sorted_and_deduped():
    refs = find_dangling_refs(
        live_card_ids=set(),
        review_card_ids={"z", "a", "a"},
        variation_card_ids=set(),
        parent_links={},
    )
    assert refs.review_logs == ["a", "z"]
