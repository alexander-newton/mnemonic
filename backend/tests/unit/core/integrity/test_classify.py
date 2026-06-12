"""Tests for the change-classification decision table."""

from __future__ import annotations

from mnemonic.core.integrity.classify import (
    CurrentHashes,
    StoredHashes,
    classify_change,
)


def _stored(h="h1", n="n1", c="c1"):
    return StoredHashes(core_hash=h, core_hash_normalized=n, cloze_signature=c)


def _current(h="h1", n="n1", c="c1"):
    return CurrentHashes(core_hash=h, core_hash_normalized=n, cloze_signature=c)


def test_new_when_stored_is_none():
    assert classify_change(None, _current()).kind == "new"


def test_new_when_stored_core_hash_is_none():
    assert classify_change(_stored(h=None), _current()).kind == "new"


def test_unchanged_when_all_equal():
    assert classify_change(_stored(), _current()).kind == "unchanged"


def test_trivial_when_only_raw_differs():
    stored = _stored(h="old")
    current = _current(h="new")  # normalized + cloze unchanged
    assert classify_change(stored, current).kind == "trivial"


def test_material_when_normalized_differs():
    stored = _stored(h="old", n="oldnorm")
    current = _current(h="new", n="newnorm")  # cloze unchanged
    assert classify_change(stored, current).kind == "material"


def test_cloze_structure_when_cloze_signature_differs():
    stored = _stored(h="old", c="oldcloze")
    current = _current(h="new", c="newcloze")
    assert classify_change(stored, current).kind == "cloze_structure"


def test_cloze_structure_takes_precedence_over_material():
    # both normalized and cloze changed -> structural wins
    stored = _stored(h="old", n="oldnorm", c="oldcloze")
    current = _current(h="new", n="newnorm", c="newcloze")
    assert classify_change(stored, current).kind == "cloze_structure"
