"""Variation generation: pick target cards and drive the generate → persist pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Engine

from mnemonic.db.models import ReviewLog, TrainingExample, VariationMeta
from mnemonic.db.sqlite import session_scope
from mnemonic.vault.note import parse_note
from mnemonic.vault.repository import Card, VaultRepository


@dataclass(frozen=True)
class GenerationTarget:
    """A card selected for variation generation."""

    card: Card
    deck_folder: str


def _covered_card_ids(engine: Engine, card_ids: list[str]) -> set[str]:
    """card_ids that already have at least one non-invalidated variation."""
    if not card_ids:
        return set()
    with session_scope(engine) as s:
        rows = (
            s.query(VariationMeta.card_id)
            .filter(
                VariationMeta.card_id.in_(card_ids),
                VariationMeta.invalidated_at.is_(None),
            )
            .distinct()
            .all()
        )
    return {row[0] for row in rows}


def select_targets(
    repo: VaultRepository, engine: Engine, *, deck: str | None, limit: int
) -> list[GenerationTarget]:
    """Cards eligible for generation: enabled deck, not suspended, no live variation.

    Args:
        repo: Vault repository (source of truth for which cards exist).
        engine: SQLAlchemy engine for the state DB.
        deck: Optional deck-folder name filter.
        limit: Maximum number of targets to return.

    Returns:
        Up to ``limit`` targets, ordered by card_id for deterministic runs.
    """
    decks = {d.folder.name: d for d in repo.list_decks()}
    eligible: list[Card] = []
    for card in repo.list_cards():
        folder = card.deck_folder.name
        if deck is not None and folder != deck:
            continue
        if card.suspended:
            continue
        cfg = decks[folder].config if folder in decks else None
        if cfg is None or not cfg.variation_enabled:
            continue
        eligible.append(card)

    covered = _covered_card_ids(engine, [c.card_id for c in eligible])
    chosen = sorted((c for c in eligible if c.card_id not in covered), key=lambda c: c.card_id)
    return [GenerationTarget(card=c, deck_folder=c.deck_folder.name) for c in chosen[:limit]]


def note_inputs(note_path: Path) -> tuple[str, str]:
    """Return (raw ``## Card`` section, ``## Context`` section) for a note.

    The card section keeps its cloze markers — the prompt needs the raw form, not the
    display faces produced by ``build_faces``.
    """
    note = parse_note(note_path.read_text())
    return (note.card_section or ""), (note.context_section or "")


def recent_ratings(engine: Engine, card_id: str, *, n: int = 5) -> list[int]:
    """The card's most recent review ratings, newest first, capped at ``n``."""
    with session_scope(engine) as s:
        rows = (
            s.query(ReviewLog.rating)
            .filter(ReviewLog.card_id == card_id)
            .order_by(ReviewLog.review_time.desc())
            .limit(n)
            .all()
        )
    return [row[0] for row in rows]


def prior_variations(engine: Engine, card_id: str) -> list[dict[str, Any]]:
    """Existing live variations for a card as ``{q, a, rating}`` dicts."""
    with session_scope(engine) as s:
        rows = (
            s.query(
                TrainingExample.variation_q,
                TrainingExample.variation_a,
                TrainingExample.rating,
            )
            .join(VariationMeta, VariationMeta.id == TrainingExample.variation_id)
            .filter(
                VariationMeta.card_id == card_id,
                VariationMeta.invalidated_at.is_(None),
            )
            .all()
        )
    return [{"q": q, "a": a, "rating": rating} for q, a, rating in rows]
