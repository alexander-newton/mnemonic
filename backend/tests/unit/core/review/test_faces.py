"""Tests for building review faces (question + revealed answer)."""

from __future__ import annotations

import pytest

from mnemonic.core.review.faces import build_faces
from mnemonic.exceptions import RenderError


def test_cloze_answer_reveals_markers_in_bold():
    faces = build_faces(
        syntax="cloze",
        front="The [...] is the powerhouse. ^card-aaaabbbb",
        back="The {{c1::mitochondria}} is the powerhouse. ^card-aaaabbbb",
    )
    assert faces.front == "The [...] is the powerhouse."
    assert faces.answer == "The **mitochondria** is the powerhouse."


def test_cloze_math_is_untouched():
    faces = build_faces(
        syntax="cloze",
        front="Derivative of $x^2$ is [...]",
        back="Derivative of $x^2$ is {{c1::2x}}",
    )
    assert faces.answer == "Derivative of $x^2$ is **2x**"


def test_highlight_answer_passes_through():
    faces = build_faces(
        syntax="highlight",
        front="A [...] equilibrium.",
        back="A Nash equilibrium.",
    )
    assert faces.front == "A [...] equilibrium."
    assert faces.answer == "A Nash equilibrium."


def test_callout_answer_passes_through():
    faces = build_faces(syntax="callout", front="What is NE?", back="A stable strategy profile.")
    assert faces.answer == "A stable strategy profile."


def test_unknown_syntax_raises():
    with pytest.raises(RenderError):
        build_faces(syntax="image_cloze", front="x", back="y")
