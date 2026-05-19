"""Variation writer: persists generated variation to the note and to SQLite metadata."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from pathlib import Path

from sqlalchemy import Engine

from mnemonic.db.models import LLMUsage, VariationMeta
from mnemonic.db.sqlite import session_scope
from mnemonic.vault.injector import (
    append_variation_entry,
    ensure_variations_section,
    update_variation_rating,
)
from mnemonic.llm.variation.generator import GeneratedVariation


def persist_variation(
    *,
    engine: Engine,
    note_path: Path,
    card_id: str,
    variation: GeneratedVariation,
    vault_root: Path,
) -> str:
    """Append variation entry to note and write VariationMeta row.

    Args:
        engine: SQLAlchemy Engine for the SQLite database.
        note_path: Absolute path to the vault note file.
        card_id: The card's unique identifier (block ID).
        variation: The GeneratedVariation produced by VariationGenerator.
        vault_root: Root path of the vault, used to compute the relative note path.

    Returns:
        The generated variation_id (hex UUID).

    Raises:
        MalformedVariationSectionError: If the note's ## Variations section is malformed.
    """
    ensure_variations_section(note_path)
    date_str = datetime.now().strftime("%Y-%m-%d")
    append_variation_entry(
        note_path=note_path,
        date_str=date_str,
        question=variation.question,
        answer=variation.answer,
    )

    variation_id = uuid.uuid4().hex
    content_hash = hashlib.sha256(
        (variation.question + "\n" + variation.answer).encode()
    ).hexdigest()
    rel_path = str(note_path.relative_to(vault_root))

    now = datetime.now()
    with session_scope(engine) as s:
        s.add(VariationMeta(
            id=variation_id,
            card_id=card_id,
            strategy=variation.strategy,
            model=variation.model,
            generated_at=now,
            shown_count=1,
            helpful_count=0,
            content_hash=content_hash,
            note_path=rel_path,
        ))
        s.add(LLMUsage(
            id=uuid.uuid4().hex,
            timestamp=now,
            model=variation.model,
            purpose=f"variation:{variation.strategy}",
            input_tokens=variation.input_tokens,
            output_tokens=variation.output_tokens,
            cache_read_tokens=variation.cache_read_tokens,
            cache_creation_tokens=variation.cache_creation_tokens,
            cost_millicents=variation.cost_millicents,
            card_id=card_id,
        ))
    return variation_id


def mark_variation_rated(
    *,
    note_path: Path,
    rating: int,
) -> None:
    """Update the most recent pending entry in the note from `pending` to `rating: N`.

    Args:
        note_path: Absolute path to the vault note file.
        rating: The numeric rating (1-4) to record.

    Raises:
        MalformedVariationSectionError: If no pending entry is found for today's date.
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    update_variation_rating(note_path=note_path, date_str=date_str, rating=rating)
