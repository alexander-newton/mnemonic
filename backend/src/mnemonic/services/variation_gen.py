"""Variation generation: pick target cards and drive the generate → persist pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from sqlalchemy import Engine

from mnemonic.core.optimization.registry import get_champion
from mnemonic.core.review.faces import build_faces
from mnemonic.db.models import ReviewLog, TrainingExample, VariationMeta
from mnemonic.db.sqlite import session_scope
from mnemonic.exceptions import (
    LLMBudgetExceededError,
    LLMError,
    MalformedNoteError,
    OptimizationError,
)
from mnemonic.llm.budget import BudgetGuard
from mnemonic.llm.router import pick_model
from mnemonic.llm.variation.generator import VariationGenerator
from mnemonic.llm.variation.strategy import select_strategy
from mnemonic.llm.variation.writer import persist_variation
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


def generate_for_card(
    target: GenerationTarget,
    *,
    engine: Engine,
    generator: VariationGenerator,
    vault_root: Path,
    model_default: str,
    model_rephrase: str,
) -> str:
    """Generate and persist one variation for a card. Returns the new variation_id.

    Raises:
        LLMError: If generation fails or the response cannot be parsed.
        OptimizationError: If the strategy has no champion PromptVersion.
        MalformedNoteError: If the note cannot be parsed.
    """
    card = target.card
    card_section, context = note_inputs(card.note_path)
    ratings = recent_ratings(engine, card.card_id)
    strategy = select_strategy(reps=card.reps, lapses=card.lapses, recent_ratings=ratings)
    model = pick_model(
        strategy=strategy,
        recent_failures=sum(1 for r in ratings if r == 1),
        model_default=model_default,
        model_rephrase=model_rephrase,
    )
    with session_scope(engine) as s:
        champion = get_champion(s, strategy)
        prompt_version_id = champion.id
        instruction_text = champion.instruction_text
    variation = generator.generate(
        strategy=strategy,
        base_card_text=card_section,
        note_context=context,
        prior_variations=prior_variations(engine, card.card_id),
        fsrs={
            "stability": card.stability,
            "reps": card.reps,
            "lapses": card.lapses,
            "recent_ratings": ratings,
        },
        model=model,
        instruction_text=instruction_text,
    )
    faces = build_faces(syntax=card.syntax, front=card.front, back=card.back)
    return persist_variation(
        engine=engine,
        note_path=card.note_path,
        card_id=card.card_id,
        variation=variation,
        vault_root=vault_root,
        prompt_version_id=prompt_version_id,
        arm="champion",
        base_q=faces.front,
        base_a=faces.answer,
        note_context=context or None,
    )


@dataclass(frozen=True)
class GenerationReport:
    """Outcome of one generation run."""

    generated: list[str]
    skipped: list[tuple[str, str]]
    budget_stopped: bool
    targets: list[str]


def run_generate(
    *,
    repo: VaultRepository,
    engine: Engine,
    generator: VariationGenerator | None,
    deck: str | None,
    limit: int,
    model_default: str,
    model_rephrase: str,
    daily_cents: int,
    monthly_cents: int,
    dry_run: bool = False,
) -> GenerationReport:
    """Generate variations for eligible cards.

    Budget exhaustion stops the run; a per-card failure is recorded and skipped.

    Args:
        repo: Vault repository.
        engine: SQLAlchemy engine for state database.
        generator: VariationGenerator (required unless dry_run is True).
        deck: Optional deck-folder name filter.
        limit: Maximum number of cards to target.
        model_default: Default model for variation generation.
        model_rephrase: Model for rephrase strategy.
        daily_cents: Daily budget cap in cents.
        monthly_cents: Monthly budget cap in cents.
        dry_run: If True, return targets without generating or calling LLM.

    Returns:
        GenerationReport with generated card IDs, skipped (card_id, error) tuples,
        budget_stopped flag, and target card IDs.

    Raises:
        ValueError: If generator is None and dry_run is False.
    """
    targets = select_targets(repo, engine, deck=deck, limit=limit)
    target_ids = [t.card.card_id for t in targets]
    if dry_run:
        return GenerationReport(generated=[], skipped=[], budget_stopped=False, targets=target_ids)
    if generator is None:
        raise ValueError("A VariationGenerator is required unless dry_run=True.")

    guard = BudgetGuard(engine=engine, daily_cents=daily_cents, monthly_cents=monthly_cents)
    generated: list[str] = []
    skipped: list[tuple[str, str]] = []
    for target in targets:
        try:
            guard.assert_within_budget()
        except LLMBudgetExceededError:
            return GenerationReport(
                generated=generated,
                skipped=skipped,
                budget_stopped=True,
                targets=target_ids,
            )
        try:
            generated.append(
                generate_for_card(
                    target,
                    engine=engine,
                    generator=generator,
                    vault_root=repo.vault_root,
                    model_default=model_default,
                    model_rephrase=model_rephrase,
                )
            )
        except (LLMError, MalformedNoteError, OptimizationError, ValueError) as exc:
            skipped.append((target.card.card_id, f"{type(exc).__name__}: {exc}"))
    return GenerationReport(
        generated=generated, skipped=skipped, budget_stopped=False, targets=target_ids
    )
