"""Tests for the variation DSPy signature and module."""

from __future__ import annotations

from mnemonic.core.optimization.signatures import (
    VariationModule,
    make_variation_signature,
)


def test_signature_has_expected_fields_and_instructions():
    sig = make_variation_signature("REPHRASE INSTRUCTIONS")
    assert sig.instructions == "REPHRASE INSTRUCTIONS"
    assert set(sig.input_fields.keys()) == {"base_q", "base_a", "note_context"}
    assert set(sig.output_fields.keys()) == {"question", "answer"}


def test_module_wraps_a_predict_with_the_signature():
    sig = make_variation_signature("X")
    module = VariationModule(sig)
    assert module.predict.signature.instructions == "X"
