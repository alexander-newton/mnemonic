"""Tests for the brace-aware cloze scanner."""

from __future__ import annotations

import pytest

from mnemonic.core.cloze import Cloze, findall, iter_clozes, sub


@pytest.mark.parametrize(
    ("body", "want"),
    [
        ("{{c1::Paris}} is in {{c2::France}}", [("1", "Paris"), ("2", "France")]),
        (r"$q = {{c1::\dfrac{a - c - q_2}{2}}}$", [("1", r"\dfrac{a - c - q_2}{2}")]),
        (r"{{c1::Fubini}} on {{c2::\mathbb{R}^2}}.", [("1", "Fubini"), ("2", r"\mathbb{R}^2")]),
        (r"{{c1::\frac{\sqrt{x}}{2}}}", [("1", r"\frac{\sqrt{x}}{2}")]),
        (r"{{c1::\{x\}}}", [("1", r"\{x\}")]),
        (r"{{c1::a \\}}", [("1", r"a \\")]),
        ("{{c1::}}", []),
        ("{{c1::never closed", []),
        ("{{c1::a}} {{c1::unclosed {x}", [("1", "a")]),
        ("{{c1::unclosed {x} {{c2::b}}", [("2", "b")]),
        ("{{c12::x}}", [("12", "x")]),
    ],
)
def test_findall(body: str, want: list[tuple[str, str]]) -> None:
    assert findall(body) == want


def test_iter_clozes_reports_span_of_whole_marker() -> None:
    s = r"x {{c2::\mathbb{R}}} y"
    (c,) = iter_clozes(s)
    assert c == Cloze(start=2, end=20, number="2", text=r"\mathbb{R}")
    assert s[c.start : c.end] == r"{{c2::\mathbb{R}}}"


def test_sub_reveals_every_cloze() -> None:
    s = r"{{c1::Fubini}} on {{c2::\mathbb{R}^2}}."
    assert sub(lambda c: f"**{c.text}**", s) == r"**Fubini** on **\mathbb{R}^2**."


def test_sub_without_clozes_returns_input() -> None:
    assert sub(lambda _: "X", "no markers {here}") == "no markers {here}"
