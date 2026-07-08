"""Core-change service: list flagged cards and apply the user's reset decision."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from sqlalchemy import Engine

from mnemonic.core.fsrs.defaults import NEW_CARD_DEFAULTS
from mnemonic.db.models import SchedulingState
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import CardNotFoundError, ValidationError
from mnemonic.vault.repository import VaultRepository

Decision = Literal["keep", "soft_reset", "full_reset"]
_DECISIONS = ("keep", "soft_reset", "full_reset")


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
