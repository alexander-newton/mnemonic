"""Tests for variation-generation target selection and the run loop."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import Base, TrainingExample, VariationMeta
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.variation_gen import select_targets
from mnemonic.vault.repository import VaultRepository

WHEN = datetime(2026, 7, 1, 12, 0, 0)


def _deck_md(enabled: bool = True) -> str:
    return (
        f"---\ndeck_name: GT\nvariation_enabled: {str(enabled).lower()}\n"
        "variation_frequency: 1.0\nleech_threshold: 8\n"
        "daily_review_limit: 100\ndaily_new_limit: 10\n---\n"
    )


def _card_note(n: int) -> str:
    # Use valid hex block IDs; inject_block_id generates card-XXXXXXXX format
    block_id = f"{n:08x}"
    return f"---\ntitle: n{n}\n---\n## Card\n\nA {{{{c1::term{n}}}}}. ^card-{block_id}\n"


def _setup(tmp_path: Path, *, enabled: bool = True, n_cards: int = 3):
    vault = tmp_path / "vault"
    deck = vault / "01_Projects" / "gt"
    deck.mkdir(parents=True)
    (deck / "_deck.md").write_text(_deck_md(enabled))
    for i in range(n_cards):
        (deck / f"n{i}.qmd").write_text(_card_note(i))
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return VaultRepository(vault_root=vault, engine=engine), engine


def _add_variation(engine, card_id: str, vid: str, *, invalidated=None):
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id=vid,
                card_id=card_id,
                strategy="rephrase",
                model="m",
                generated_at=WHEN,
                shown_count=0,
                helpful_count=0,
                content_hash="h",
                note_path="n.qmd",
                invalidated_at=invalidated,
            )
        )
        s.add(
            TrainingExample(
                id=f"te-{vid}",
                card_id=card_id,
                variation_id=vid,
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=0,
                created_at=WHEN,
            )
        )


def test_targets_are_cards_without_live_variations(tmp_path: Path):
    repo, engine = _setup(tmp_path)
    _add_variation(engine, "card-00000000", "v0")  # n0 already covered

    targets = select_targets(repo, engine, deck=None, limit=10)

    assert [t.card.card_id for t in targets] == ["card-00000001", "card-00000002"]


def test_invalidated_variations_do_not_count_as_coverage(tmp_path: Path):
    repo, engine = _setup(tmp_path, n_cards=1)
    _add_variation(engine, "card-00000000", "v0", invalidated=WHEN)

    targets = select_targets(repo, engine, deck=None, limit=10)

    assert [t.card.card_id for t in targets] == ["card-00000000"]


def test_disabled_deck_yields_no_targets(tmp_path: Path):
    repo, engine = _setup(tmp_path, enabled=False)
    assert select_targets(repo, engine, deck=None, limit=10) == []


def test_limit_caps_targets(tmp_path: Path):
    repo, engine = _setup(tmp_path, n_cards=5)
    assert len(select_targets(repo, engine, deck=None, limit=2)) == 2


def test_deck_filter(tmp_path: Path):
    repo, engine = _setup(tmp_path)
    assert select_targets(repo, engine, deck="gt", limit=10) != []
    assert select_targets(repo, engine, deck="other", limit=10) == []
