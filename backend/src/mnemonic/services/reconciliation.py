"""Reconciliation pass: detect core changes, orphans, and duplicates during a scan.

This is the single stateful caller of the pure ``core/integrity`` functions. It reads
stored hashes, classifies each card's change, applies the action matrix from the design
spec (auto-invalidate reversible artefacts; flag — never reset — FSRS), and returns a
structured report. Runs inside one transaction: any per-card IntegrityError aborts the
whole pass loudly with no partial commit.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine, select
from sqlalchemy.orm import Session

from mnemonic.core.integrity.classify import (
    ChangeVerdict,
    CurrentHashes,
    StoredHashes,
    classify_change,
)
from mnemonic.core.integrity.duplicates import DuplicateGroup, find_duplicates
from mnemonic.core.integrity.hashing import (
    cloze_signature,
    compute_core_hash,
    compute_normalized_hash,
)
from mnemonic.core.integrity.orphans import DanglingRefs, find_dangling_refs
from mnemonic.db.models import (
    CoreChangeLog,
    ReviewLog,
    SchedulingState,
    TrainingExample,
    VariationMeta,
)
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import IntegrityError
from mnemonic.vault.scanner import ScannedCard, scan_vault

_KINDS = ("new", "unchanged", "trivial", "material", "cloze_structure")
_FLAGGED = ("material", "cloze_structure")


@dataclass
class ReconciliationReport:
    """Outcome of one reconciliation pass.

    Attributes:
        counts: number of cards per change kind.
        dangling: dangling review/variation/parent references.
        duplicates: groups of cards sharing a normalized core hash.
    """

    counts: dict[str, int]
    dangling: DanglingRefs
    duplicates: list[DuplicateGroup]


class ReconciliationService:
    """Run the change/orphan/duplicate detection pass over a vault + SQLite engine."""

    def __init__(self, vault_root: Path, engine: Engine) -> None:
        self.vault_root = vault_root
        self.engine = engine

    def run(self) -> ReconciliationReport:
        """Scan the vault, reconcile every card, and detect orphans and duplicates."""
        scanned = list(scan_vault(self.vault_root, inject_missing_ids=True))
        live_ids = {sc.card_id for sc in scanned}
        counts = dict.fromkeys(_KINDS, 0)
        normalized_by_card: dict[str, str] = {}
        now = datetime.now()
        with session_scope(self.engine) as session:
            for sc in scanned:
                current = self._hash_card(sc)
                normalized_by_card[sc.card_id] = current.core_hash_normalized
                verdict = self._reconcile_card(session, sc, current, now)
                counts[verdict.kind] += 1
            dangling = self._check_orphans(session, live_ids, now)
        duplicates = find_duplicates(normalized_by_card)
        return ReconciliationReport(counts=counts, dangling=dangling, duplicates=duplicates)

    def _hash_card(self, sc: ScannedCard) -> CurrentHashes:
        """Compute all three hashes for a scanned card, re-raising empties with context."""
        try:
            return CurrentHashes(
                core_hash=compute_core_hash(sc.back),
                core_hash_normalized=compute_normalized_hash(sc.back),
                cloze_signature=cloze_signature(sc.back),
            )
        except IntegrityError as exc:
            raise IntegrityError(
                f"Card {sc.card_id} in {sc.note_path} has an empty core body — "
                "cannot hash. The note may be malformed."
            ) from exc

    def _reconcile_card(
        self, session: Session, sc: ScannedCard, current: CurrentHashes, now: datetime
    ) -> ChangeVerdict:
        """Classify one card and apply the resulting action matrix."""
        row = session.get(SchedulingState, sc.card_id)
        stored = (
            StoredHashes(row.core_hash, row.core_hash_normalized, row.cloze_signature)
            if row is not None
            else None
        )
        verdict = classify_change(stored, current)
        self._apply_verdict(session, sc, row, current, verdict, now)
        return verdict

    def _apply_verdict(
        self,
        session: Session,
        sc: ScannedCard,
        row: SchedulingState | None,
        current: CurrentHashes,
        verdict: ChangeVerdict,
        now: datetime,
    ) -> None:
        """Write hashes, set flags, invalidate derived artefacts, and log the change."""
        if verdict.kind == "unchanged":
            return
        old_hash = row.core_hash if row is not None else None
        old_norm = row.core_hash_normalized if row is not None else None
        if row is None:
            row = SchedulingState(card_id=sc.card_id)
            session.add(row)
        row.core_hash = current.core_hash
        row.core_hash_normalized = current.core_hash_normalized
        row.cloze_signature = current.cloze_signature
        if verdict.kind in _FLAGGED:
            row.core_changed = True
            row.core_changed_at = now
            self._invalidate_derived(session, sc.card_id, now)
        self._log_change(session, sc.card_id, old_hash, old_norm, current, verdict, now)

    @staticmethod
    def _invalidate_derived(session: Session, card_id: str, now: datetime) -> None:
        """Mark all still-active variations and training examples for this card stale."""
        session.query(VariationMeta).filter(
            VariationMeta.card_id == card_id,
            VariationMeta.invalidated_at.is_(None),
        ).update({VariationMeta.invalidated_at: now})
        session.query(TrainingExample).filter(
            TrainingExample.card_id == card_id,
            TrainingExample.invalidated_at.is_(None),
        ).update({TrainingExample.invalidated_at: now})

    @staticmethod
    def _log_change(
        session: Session,
        card_id: str,
        old_hash: str | None,
        old_norm: str | None,
        current: CurrentHashes,
        verdict: ChangeVerdict,
        now: datetime,
    ) -> None:
        """Append one CoreChangeLog audit row."""
        session.add(
            CoreChangeLog(
                id=uuid.uuid4().hex,
                card_id=card_id,
                change_kind=verdict.kind,
                old_hash=old_hash,
                new_hash=current.core_hash,
                old_normalized=old_norm,
                new_normalized=current.core_hash_normalized,
                detected_at=now,
            )
        )

    def _check_orphans(self, session: Session, live_ids: set[str], now: datetime) -> DanglingRefs:
        """Find and apply dangling-reference consequences."""
        review_ids = {r[0] for r in session.execute(select(ReviewLog.card_id)).all()}
        variation_ids = {r[0] for r in session.execute(select(VariationMeta.card_id)).all()}
        parent_links = {
            r[0]: r[1]
            for r in session.execute(
                select(SchedulingState.card_id, SchedulingState.parent_card_id).where(
                    SchedulingState.parent_card_id.is_not(None)
                )
            ).all()
        }
        dangling = find_dangling_refs(live_ids, review_ids, variation_ids, parent_links)
        self._apply_orphans(session, dangling, now)
        return dangling

    @staticmethod
    def _apply_orphans(session: Session, dangling: DanglingRefs, now: datetime) -> None:
        """Flag orphaned children and invalidate orphaned variations. Review logs untouched."""
        for child_id in dangling.parents:
            row = session.get(SchedulingState, child_id)
            if row is not None:
                row.orphan = True
        for card_id in dangling.variations:
            session.query(VariationMeta).filter(
                VariationMeta.card_id == card_id,
                VariationMeta.invalidated_at.is_(None),
            ).update({VariationMeta.invalidated_at: now})
