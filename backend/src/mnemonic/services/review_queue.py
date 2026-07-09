"""Review queue: build an ordered list of cards to review for a deck.

`ReviewPolicy` is the seam the future cascading-rules engine (B1-Policy) plugs into.
`SimplePolicy` is the B1-Loop placeholder: due review cards ordered by due, then new
cards capped at the deck's daily_new_limit.
"""

from __future__ import annotations

from datetime import datetime
from typing import Protocol

from mnemonic.vault.repository import Card


class ReviewPolicy(Protocol):
    """Produces the ordered set of cards to review now."""

    def build_queue(self, cards: list[Card], now: datetime, daily_new_limit: int) -> list[Card]: ...


class SimplePolicy:
    """Due review cards (by due asc) then new cards capped at daily_new_limit."""

    def build_queue(self, cards: list[Card], now: datetime, daily_new_limit: int) -> list[Card]:
        due = [
            c
            for c in cards
            if not c.suspended and c.state != "new" and c.due is not None and c.due <= now
        ]
        due.sort(key=lambda c: c.due or now)
        new = [c for c in cards if not c.suspended and c.state == "new"][:daily_new_limit]
        return due + new
