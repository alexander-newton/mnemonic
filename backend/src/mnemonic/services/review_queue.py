"""Review queue: build an ordered list of cards to review for a deck.

`ReviewPolicy` is the seam the future cascading-rules engine (B1-Policy) plugs into.
`SimplePolicy` is the B1-Loop placeholder: due review cards ordered by due, then new
cards capped at the deck's daily_new_limit.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import Engine

from mnemonic.core.fsrs.preview import preview_schedule
from mnemonic.core.fsrs.state import to_card_state
from mnemonic.core.review.faces import build_faces
from mnemonic.db.models import ReviewLog
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import DeckNotFoundError
from mnemonic.vault.repository import Card, VaultRepository


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


_DEFAULT_NEW_LIMIT = 20


@dataclass(frozen=True)
class QueuedCard:
    """One card ready to review: both faces plus per-rating preview intervals (days)."""

    card_id: str
    syntax: str
    front: str
    answer: str
    previews: dict[int, int]


class QueueService:
    """Build an ordered, display-ready review queue for a deck."""

    def __init__(
        self, *, repo: VaultRepository, engine: Engine, policy: ReviewPolicy | None = None
    ) -> None:
        self.repo = repo
        self.engine = engine
        self.policy = policy or SimplePolicy()

    def build(self, deck_folder: str) -> list[QueuedCard]:
        """Resolve the deck, order its cards by policy, and build display items.

        Raises:
            DeckNotFoundError: If no deck folder with that name exists.
        """
        now = datetime.now()
        deck = next((d for d in self.repo.list_decks() if d.folder.name == deck_folder), None)
        if deck is None:
            raise DeckNotFoundError(
                f"Deck '{deck_folder}' not found in the vault. Check the deck folder name."
            )
        cards = [c for c in self.repo.list_cards() if c.deck_folder.name == deck_folder]
        limit = deck.config.daily_new_limit if deck.config else _DEFAULT_NEW_LIMIT
        ordered = self.policy.build_queue(cards, now, limit)
        last_reviews = self._last_reviews([c.card_id for c in ordered])
        return [self._to_item(c, last_reviews.get(c.card_id), now) for c in ordered]

    def _last_reviews(self, card_ids: list[str]) -> dict[str, datetime]:
        if not card_ids:
            return {}
        with session_scope(self.engine) as s:
            rows = (
                s.query(ReviewLog.card_id, ReviewLog.review_time)
                .filter(ReviewLog.card_id.in_(card_ids))
                .all()
            )
        latest: dict[str, datetime] = {}
        for cid, when in rows:
            if cid not in latest or when > latest[cid]:
                latest[cid] = when
        return latest

    def _to_item(self, card: Card, last_review: datetime | None, now: datetime) -> QueuedCard:
        faces = build_faces(syntax=card.syntax, front=card.front, back=card.back)
        state = to_card_state(
            stability=card.stability,
            difficulty=card.difficulty,
            reps=card.reps,
            lapses=card.lapses,
            state=card.state,
            due=card.due,
            last_review=last_review,
            now=now,
        )
        previews = {r: opt.new_interval for r, opt in preview_schedule(state).items()}
        return QueuedCard(
            card_id=card.card_id,
            syntax=card.syntax,
            front=faces.front,
            answer=faces.answer,
            previews=previews,
        )
