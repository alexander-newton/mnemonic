"""Tests for normalized-hash duplicate detection."""

from __future__ import annotations

from mnemonic.core.integrity.duplicates import find_duplicates


def test_no_duplicates_when_all_unique():
    assert find_duplicates({"a": "h1", "b": "h2"}) == []


def test_pair_duplicate_grouped():
    groups = find_duplicates({"a": "h1", "b": "h1", "c": "h2"})
    assert len(groups) == 1
    assert groups[0].normalized_hash == "h1"
    assert groups[0].card_ids == ["a", "b"]


def test_triple_duplicate_grouped():
    groups = find_duplicates({"x": "h", "y": "h", "z": "h"})
    assert len(groups) == 1
    assert groups[0].card_ids == ["x", "y", "z"]


def test_card_ids_sorted_within_group():
    groups = find_duplicates({"b": "h", "a": "h"})
    assert groups[0].card_ids == ["a", "b"]
