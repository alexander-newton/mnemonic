"""Build the two display faces of a card: the question and the revealed answer.

Output is clean markdown (math untouched, block-ID token removed). Cloze answers are
revealed in bold; highlight/callout backs are already revealed and pass through.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from mnemonic.core import cloze
from mnemonic.exceptions import RenderError

_BLOCK_ID_RE = re.compile(r"\^card-[0-9a-z]+")


@dataclass(frozen=True)
class ReviewFaces:
    """The question face and the revealed-answer face, both clean markdown."""

    front: str
    answer: str


def _strip_block_id(text: str) -> str:
    """Strip block-ID tokens and trailing whitespace.

    Args:
        text: Text potentially containing ^card-xxxx tokens.

    Returns:
        Text with tokens removed and trailing whitespace stripped.
    """
    return _BLOCK_ID_RE.sub("", text).strip()


def build_faces(*, syntax: str, front: str, back: str) -> ReviewFaces:
    """Produce (front, answer) markdown faces for a card.

    Args:
        syntax: "cloze" | "highlight" | "callout".
        front: The blanked question text from the extractor.
        back: The extractor's back text (raw cloze markers for cloze; revealed otherwise).

    Returns:
        ReviewFaces with block-ID-stripped, revealed markdown.

    Raises:
        RenderError: If ``syntax`` is not a supported display syntax.
    """
    if syntax == "cloze":
        answer = cloze.sub(lambda c: f"**{c.text}**", back)
    elif syntax in ("highlight", "callout"):
        answer = back
    else:
        raise RenderError(f"Cannot build review faces for unsupported card syntax '{syntax}'.")
    return ReviewFaces(front=_strip_block_id(front), answer=_strip_block_id(answer))
