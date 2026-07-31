"""Review queue: build an ordered, display-ready list of cards to review for a deck.

`ReviewPolicy` is the seam the policy engine plugs into; `RulesPolicy` selects and orders
cards from a resolved `EffectivePolicy` plus today's done-counts.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from sqlalchemy import Engine, func

from mnemonic.core.fsrs.preview import preview_schedule
from mnemonic.core.fsrs.state import to_card_state
from mnemonic.core.policy.resolve import EffectivePolicy, Limits, SeedLimits, resolve_policy
from mnemonic.core.policy.rules import load_rules
from mnemonic.core.review.faces import build_faces
from mnemonic.core.variation.choose import VariationCandidate, choose_variation
from mnemonic.db.models import ReviewLog, TrainingExample, VariationMeta
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import DeckNotFoundError
from mnemonic.vault.repository import Card, VaultRepository

_DEFAULT_LIMIT = 20


@dataclass(frozen=True)
class DoneToday:
    """Cards already reviewed today for a deck, split by new vs due."""

    new: int
    due: int
    total: int


@dataclass(frozen=True)
class QueueContext:
    """Everything a policy needs to build a queue."""

    cards: list[Card]
    now: datetime
    policy: EffectivePolicy
    done_today: DoneToday
    seed: int


class ReviewPolicy(Protocol):
    """Produces the ordered set of cards to review now."""

    def build_queue(self, ctx: QueueContext) -> list[Card]: ...


def _cap(limits: Limits, done: int) -> int | None:
    caps: list[int] = []
    if limits.per_day is not None:
        caps.append(max(0, limits.per_day - done))
    if limits.per_session is not None:
        caps.append(max(0, limits.per_session))
    return min(caps) if caps else None


def _take(items: list[Card], cap: int | None) -> list[Card]:
    return items if cap is None else items[:cap]


def _interleave(due: list[Card], new: list[Card], every: int) -> list[Card]:
    out: list[Card] = []
    di = ni = 0
    while di < len(due) or ni < len(new):
        for _ in range(every):
            if di < len(due):
                out.append(due[di])
                di += 1
        if ni < len(new):
            out.append(new[ni])
            ni += 1
    return out


def _order(order: str, due: list[Card], new: list[Card], ine: int | None, seed: int) -> list[Card]:
    if order == "new_first":
        return new + due
    if order == "shuffle":
        combined = due + new
        random.Random(seed).shuffle(combined)
        return combined
    if order == "interleave" and ine is not None:
        return _interleave(due, new, ine)
    return due + new  # due_first (default)


class RulesPolicy:
    """Select cards within resolved limits and order them per the effective policy."""

    def build_queue(self, ctx: QueueContext) -> list[Card]:
        p = ctx.policy
        due_all = sorted(
            [
                c
                for c in ctx.cards
                if not c.suspended and c.state != "new" and c.due is not None and c.due <= ctx.now
            ],
            key=lambda c: c.due or ctx.now,
        )
        new_all = [c for c in ctx.cards if not c.suspended and c.state == "new"]
        due = _take(due_all, _cap(p.due, ctx.done_today.due))
        new = _take(new_all, _cap(p.new, ctx.done_today.new))
        ordered = _order(p.order, due, new, p.interleave_new_every, ctx.seed)
        return _take(ordered, _cap(p.all, ctx.done_today.total))


@dataclass(frozen=True)
class QueuedCard:
    """One card ready to review: both faces plus per-rating preview intervals (days)."""

    card_id: str
    syntax: str
    front: str
    answer: str
    previews: dict[int, int]
    variation_id: str | None = None
    variation_front: str | None = None
    variation_answer: str | None = None


@dataclass(frozen=True)
class QueueLimits:
    """Limits the frontend must enforce (time/session is wall-clock at runtime)."""

    minutes_per_session: int | None


@dataclass(frozen=True)
class QueueResult:
    """The built queue plus the client-enforced limits."""

    cards: list[QueuedCard]
    limits: QueueLimits


class QueueService:
    """Assemble a display-ready review queue: resolve policy, count today, order, render."""

    def __init__(
        self,
        *,
        repo: VaultRepository,
        engine: Engine,
        default_new_per_day: int = _DEFAULT_LIMIT,
        default_due_per_day: int = _DEFAULT_LIMIT,
        policy: ReviewPolicy | None = None,
    ) -> None:
        self.repo = repo
        self.engine = engine
        self.default_new_per_day = default_new_per_day
        self.default_due_per_day = default_due_per_day
        self.policy = policy or RulesPolicy()

    def build(self, deck_folder: str) -> QueueResult:
        """Build the queue for a deck.

        Raises:
            DeckNotFoundError: If no deck folder with that name exists.
            PolicyError: If the vault's policy.toml is malformed.
        """
        now = datetime.now()
        deck = next((d for d in self.repo.list_decks() if d.folder.name == deck_folder), None)
        if deck is None:
            raise DeckNotFoundError(
                f"Deck '{deck_folder}' not found in the vault. Check the deck folder name."
            )
        cards = [c for c in self.repo.list_cards() if c.deck_folder.name == deck_folder]
        seed_limits = SeedLimits(
            new_per_day=deck.config.daily_new_limit if deck.config else self.default_new_per_day,
            due_per_day=deck.config.daily_review_limit if deck.config else self.default_due_per_day,
        )
        effective = resolve_policy(
            seed=seed_limits, rules=load_rules(self.repo.vault_root), deck=deck_folder
        )
        limits = QueueLimits(minutes_per_session=effective.minutes_per_session)
        if (
            effective.minutes_per_day is not None
            and self._minutes_today(deck_folder, now) >= effective.minutes_per_day
        ):
            return QueueResult(cards=[], limits=limits)
        ctx = QueueContext(
            cards=cards,
            now=now,
            policy=effective,
            done_today=self._done_today(deck_folder, now),
            seed=now.toordinal(),
        )
        ordered = self.policy.build_queue(ctx)
        last_reviews = self._last_reviews([c.card_id for c in ordered])
        candidates = self._variation_candidates([c.card_id for c in ordered])
        var_enabled = deck.config.variation_enabled if deck.config else False
        var_frequency = deck.config.variation_frequency if deck.config else 0.0
        rng = random.Random(ctx.seed)
        items = [
            self._to_item(
                c,
                last_reviews.get(c.card_id),
                now,
                choose_variation(
                    candidates.get(c.card_id, []),
                    enabled=var_enabled,
                    frequency=var_frequency,
                    roll=rng.random(),
                ),
            )
            for c in ordered
        ]
        return QueueResult(cards=items, limits=limits)

    def _minutes_today(self, deck_folder: str, now: datetime) -> int:
        start = datetime(now.year, now.month, now.day)
        with session_scope(self.engine) as s:
            total_ms = (
                s.query(func.coalesce(func.sum(ReviewLog.response_time_ms), 0))
                .filter(ReviewLog.deck_folder == deck_folder, ReviewLog.review_time >= start)
                .scalar()
            )
        return int(total_ms) // 60_000

    def _done_today(self, deck_folder: str, now: datetime) -> DoneToday:
        start = datetime(now.year, now.month, now.day)
        with session_scope(self.engine) as s:
            rows = (
                s.query(ReviewLog.state_before, func.count())
                .filter(ReviewLog.deck_folder == deck_folder, ReviewLog.review_time >= start)
                .group_by(ReviewLog.state_before)
                .all()
            )
        new = sum(n for sb, n in rows if sb == "new")
        due = sum(n for sb, n in rows if sb != "new")
        return DoneToday(new=new, due=due, total=new + due)

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

    def _variation_candidates(self, card_ids: list[str]) -> dict[str, list[VariationCandidate]]:
        """Non-invalidated variations per card, joined to their displayable Q/A text."""
        if not card_ids:
            return {}
        with session_scope(self.engine) as s:
            rows = (
                s.query(
                    VariationMeta.card_id,
                    VariationMeta.id,
                    TrainingExample.variation_q,
                    TrainingExample.variation_a,
                    VariationMeta.shown_count,
                    VariationMeta.generated_at,
                )
                .join(TrainingExample, TrainingExample.variation_id == VariationMeta.id)
                .filter(
                    VariationMeta.card_id.in_(card_ids),
                    VariationMeta.invalidated_at.is_(None),
                )
                .all()
            )
        out: dict[str, list[VariationCandidate]] = {}
        for card_id, vid, question, answer, shown, generated in rows:
            out.setdefault(card_id, []).append(
                VariationCandidate(
                    variation_id=vid,
                    question=question,
                    answer=answer,
                    shown_count=shown,
                    generated_at=generated,
                )
            )
        return out

    def _to_item(
        self,
        card: Card,
        last_review: datetime | None,
        now: datetime,
        variation: VariationCandidate | None = None,
    ) -> QueuedCard:
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
            variation_id=variation.variation_id if variation else None,
            variation_front=variation.question if variation else None,
            variation_answer=variation.answer if variation else None,
        )
