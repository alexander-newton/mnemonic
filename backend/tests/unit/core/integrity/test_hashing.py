"""Tests for pure card-core hashing."""

from __future__ import annotations

import pytest

from mnemonic.core.integrity.hashing import (
    cloze_signature,
    compute_core_hash,
    compute_normalized_hash,
    normalize_core,
)
from mnemonic.exceptions import IntegrityError

_BODY = "What is a Nash equilibrium? ^card-aaaabbbb"


def test_block_id_excluded_from_raw_hash():
    with_id = "Define NE. ^card-aaaabbbb"
    without_id = "Define NE."
    assert compute_core_hash(with_id) == compute_core_hash(without_id)


def test_raw_hash_changes_with_content():
    assert compute_core_hash("Define NE.") != compute_core_hash("Define dominance.")


def test_normalize_folds_case_and_whitespace():
    assert normalize_core("Define   NE.") == normalize_core("define ne.")


def test_normalized_hash_ignores_trivial_formatting():
    assert compute_normalized_hash("Define  NE.") == compute_normalized_hash("define ne.")


def test_normalize_is_idempotent():
    once = normalize_core(_BODY)
    assert normalize_core(once) == once


def test_normalize_reduces_cloze_markers_to_inner_text():
    assert normalize_core("the {{c1::mitochondria}} is the powerhouse") == normalize_core(
        "the mitochondria is the powerhouse"
    )


def test_normalize_nfc_equivalence():
    composed = "café"  # é as one code point
    decomposed = "café"  # e + combining acute
    assert normalize_core(composed) == normalize_core(decomposed)


def test_empty_core_raises_on_raw_hash():
    with pytest.raises(IntegrityError):
        compute_core_hash("   ^card-aaaabbbb  ")


def test_empty_core_raises_on_normalized_hash():
    with pytest.raises(IntegrityError):
        compute_normalized_hash("  ")


def test_cloze_signature_none_when_no_cloze():
    assert cloze_signature("plain ==highlight== card") is None


def test_cloze_signature_stable_under_reordering_in_text():
    a = "{{c1::alpha}} then {{c2::beta}}"
    b = "{{c2::beta}} first {{c1::alpha}}"
    assert cloze_signature(a) == cloze_signature(b)


def test_cloze_signature_changes_when_number_changes():
    assert cloze_signature("{{c1::alpha}}") != cloze_signature("{{c2::alpha}}")


def test_normalize_core_declozes_answers_with_braces():
    body = r"Best response is $q_1 = {{c1::\dfrac{a - c - q_2}{2}}}$."
    assert normalize_core(body) == r"best response is $q_1 = \dfrac{a - c - q_2}{2}$."


def test_cloze_signature_sees_answers_with_braces():
    assert cloze_signature(r"$q = {{c1::\dfrac{a}{2}}}$") is not None
    one = cloze_signature(r"{{c1::Fubini}} on {{c2::\mathbb{R}^2}}.")
    other = cloze_signature(r"{{c1::Fubini}} on {{c2::\mathbb{R}^3}}.")
    assert one != other
