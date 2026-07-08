"""Core-change service: list flagged cards and apply the user's reset decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import Engine
from sqlalchemy.orm import Session

from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS
from mnemonic.db.models import CoreChangeLog, SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.vault.repository import VaultRepository

Decision = Literal["keep", "soft_reset", "full_reset"]
_DECISIONS = ("keep", "soft_reset", "full_reset")

# card_id -> (state, due, stability, difficulty, core_changed_at)
_FlaggedRow = tuple[str, "datetime | None", float, float, "datetime | None"]


@dataclass(frozen=True)
class ChangedCard:
    """A flagged card enriched with its content and the reason it was flagged."""

    card_id: str
    title: str
    front: str
    syntax: str
    change_kind: str | None
    core_changed_at: datetime | None
    state: str
    due: datetime | None
    stability: float
    difficulty: float


@dataclass(frozen=True)
class SchedulingSnapshot:
    """The scheduling state of a card after a decision is applied."""

    card_id: str
    core_changed: bool
    state: str
    stability: float
    difficulty: float
    due: datetime | None
    reps: int
    lapses: int


class CoreChangeService:
    """List core-changed cards and apply keep / soft-reset / full-reset."""

    def __init__(self, *, repo: VaultRepository, engine: Engine) -> None:
        self.repo = repo
        self.engine = engine

    def apply(self, *, card_id: str, decision: str, now: datetime) -> SchedulingSnapshot:
        """Apply a decision to a flagged card and clear its flag.

        Args:
            card_id: The card to act on.
            decision: One of "keep", "soft_reset", "full_reset".
            now: Timestamp used as the new due date for a soft reset.

        Returns:
            A SchedulingSnapshot of the card after the change.

        Raises:
            ValidationError: If ``decision`` is not a known value.
            CardNotFoundError: If the card has no scheduling row or is not flagged.
        """
        if decision not in _DECISIONS:
            raise ValidationError(
                f"Unknown core-change decision '{decision}'. Expected one of {_DECISIONS}."
            )
        with session_scope(self.engine) as s:
            row = s.get(SchedulingState, card_id)
            if row is None or not row.core_changed:
                raise CardNotFoundError(
                    f"Card '{card_id}' is not flagged as changed — nothing to resolve. "
                    "Run a reconciliation scan, or refresh the changed-cards list."
                )
            self._apply_decision(row, decision, now)
            row.core_changed = False
            row.core_changed_at = None
            return SchedulingSnapshot(
                card_id=row.card_id,
                core_changed=False,
                state=row.state,
                stability=row.stability,
                difficulty=row.difficulty,
                due=row.due,
                reps=row.reps,
                lapses=row.lapses,
            )

    def list_changed(self) -> list[ChangedCard]:
        """Return flagged cards, enriched with content and their latest change kind.

        Cards flagged but no longer present in the vault (orphaned) are skipped.
        """
        with session_scope(self.engine) as s:
            rows = s.query(SchedulingState).filter(SchedulingState.core_changed.is_(True)).all()
            flagged: dict[str, _FlaggedRow] = {
                r.card_id: (r.state, r.due, r.stability, r.difficulty, r.core_changed_at)
                for r in rows
            }
            kinds = self._latest_kinds(s, list(flagged))
        return self._join_cards(flagged, kinds)

    @staticmethod
    def _latest_kinds(session: Session, card_ids: list[str]) -> dict[str, str]:
        """Map each card_id to its most recent CoreChangeLog.change_kind."""
        if not card_ids:
            return {}
        logs = (
            session.query(CoreChangeLog)
            .filter(CoreChangeLog.card_id.in_(card_ids))
            .order_by(CoreChangeLog.detected_at.desc())
            .all()
        )
        latest: dict[str, str] = {}
        for log in logs:
            latest.setdefault(log.card_id, log.change_kind)
        return latest

    def _join_cards(
        self, flagged: dict[str, _FlaggedRow], kinds: dict[str, str]
    ) -> list[ChangedCard]:
        """Join flagged scheduling rows with vault card content."""
        cards = {c.card_id: c for c in self.repo.list_cards()}
        out: list[ChangedCard] = []
        for card_id, (state, due, stability, difficulty, changed_at) in flagged.items():
            card = cards.get(card_id)
            if card is None:
                continue
            out.append(
                ChangedCard(
                    card_id=card_id,
                    title=card.title,
                    front=card.front,
                    syntax=card.syntax,
                    change_kind=kinds.get(card_id),
                    core_changed_at=changed_at,
                    state=state,
                    due=due,
                    stability=stability,
                    difficulty=difficulty,
                )
            )
        out.sort(key=lambda c: (c.core_changed_at or datetime.min), reverse=True)
        return out

    @staticmethod
    def _apply_decision(row: SchedulingState, decision: str, now: datetime) -> None:
        """Mutate FSRS fields per the decision (flag clearing handled by caller)."""
        if decision == "soft_reset":
            row.due = now
        elif decision == "full_reset":
            row.state = NEW_CARD_DEFAULTS.state
            row.stability = NEW_CARD_DEFAULTS.stability
            row.difficulty = NEW_CARD_DEFAULTS.difficulty
            row.due = NEW_CARD_DEFAULTS.due
            row.reps = NEW_CARD_DEFAULTS.reps
            row.lapses = NEW_CARD_DEFAULTS.lapses
        # "keep": no FSRS change
