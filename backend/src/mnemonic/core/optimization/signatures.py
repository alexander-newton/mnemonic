"""DSPy signature and module for variation generation.

Inputs are restricted to the fields Phase 1 actually captured in
``TrainingExample`` (base_q, base_a, note_context). FSRS state and prior
variations are runtime-only context applied by the Jinja generator and are
intentionally not part of the optimized signature/demos.
"""

from __future__ import annotations

import dspy

_SIGNATURE_SPEC = "base_q, base_a, note_context -> question, answer"


def make_variation_signature(instruction_text: str) -> type[dspy.Signature]:
    """Build a variation signature seeded with the given instruction text.

    Args:
        instruction_text: The strategy instruction (a champion's instruction_text).

    Returns:
        A dspy.Signature class with base_q/base_a/note_context inputs and
        question/answer outputs.
    """
    return dspy.Signature(_SIGNATURE_SPEC, instruction_text)


class VariationModule(dspy.Module):
    """A single-Predict module over the variation signature."""

    def __init__(self, signature: type[dspy.Signature]) -> None:
        """Initialize with a variation signature.

        Args:
            signature: The signature produced by ``make_variation_signature``.
        """
        super().__init__()
        self.predict = dspy.Predict(signature)

    def forward(self, **kwargs: str) -> dspy.Prediction:
        """Generate a variation. Keyword args are the signature input fields."""
        return self.predict(**kwargs)
