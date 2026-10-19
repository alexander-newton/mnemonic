"""Brace-aware scanning of ``{{cN::answer}}`` cloze markers.

The answer may contain balanced braces (LaTeX such as ``\\frac{a}{b}`` or
``\\mathbb{R}``); a marker closes at the first ``}}`` reached at brace depth 0.
Backslash-escaped characters (``\\{``, ``\\}``) never change depth. This module is
the single source of truth for the vault extractor, integrity hashing and review faces.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Iterator
from dataclasses import dataclass

_OPEN_RE = re.compile(r"\{\{c(\d+)::")
_CLOSE = "}}"
_ESCAPE = "\\"


@dataclass(frozen=True)
class Cloze:
    """One cloze marker: its span ``[start, end)`` in the source, number and answer."""

    start: int
    end: int
    number: str
    text: str


def _find_close(s: str, pos: int) -> int | None:
    """Return the index of the ``}}`` closing a cloze whose answer starts at ``pos``.

    Args:
        s: The full source text.
        pos: Index just past the ``{{cN::`` opener.

    Returns:
        Index of the closing ``}}``, or None if the marker is never closed.
    """
    depth, i = 0, pos
    while i < len(s):
        ch = s[i]
        if ch == _ESCAPE:
            i += 2
            continue
        if ch == "{":
            depth += 1
        elif ch == "}":
            if depth:
                depth -= 1
            elif s.startswith(_CLOSE, i):
                return i
        i += 1
    return None


def iter_clozes(s: str) -> Iterator[Cloze]:
    """Yield every well-formed cloze marker in ``s``, left to right.

    An opener that is never closed is skipped and scanning resumes after it, so one
    malformed marker does not hide later ones. Empty answers (``{{c1::}}``) are not clozes.

    Args:
        s: Text that may contain cloze markers.

    Yields:
        Cloze for each marker found.
    """
    pos = 0
    while (m := _OPEN_RE.search(s, pos)) is not None:
        close = _find_close(s, m.end())
        if close is None:
            pos = m.end()
            continue
        if close > m.end():
            yield Cloze(m.start(), close + len(_CLOSE), m.group(1), s[m.end() : close])
        pos = close + len(_CLOSE)


def findall(s: str) -> list[tuple[str, str]]:
    """Return ``[(number, answer), ...]`` for every cloze in ``s``."""
    return [(c.number, c.text) for c in iter_clozes(s)]


def sub(fn: Callable[[Cloze], str], s: str) -> str:
    """Replace each cloze marker in ``s`` with ``fn(cloze)``.

    Args:
        fn: Maps a Cloze to its replacement text.
        s: Text that may contain cloze markers.

    Returns:
        ``s`` with every marker replaced; text outside markers is unchanged.
    """
    out: list[str] = []
    last = 0
    for c in iter_clozes(s):
        out += [s[last : c.start], fn(c)]
        last = c.end
    return "".join(out) + s[last:]
