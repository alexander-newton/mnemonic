"""Integration tests for the reconciliation pass over a real vault + SQLite."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import (
    Base,
    CoreChangeLog,
    SchedulingState,
    TrainingExample,
    VariationMeta,
)
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.services.reconciliation import ReconciliationService


def _vault(tmp_path: Path) -> Path:
    vault = tmp_path / "vault"
    (vault / "01_Projects" / "gt").mkdir(parents=True)
    return vault


def _write_card(vault: Path, name: str, body: str) -> Path:
    path = vault / "01_Projects" / "gt" / f"{name}.qmd"
    path.write_text(f"---\ntitle: {name}\n---\n## Card\n\n{body}\n")
    return path


def _engine(vault: Path):
    engine = create_engine(vault / ".mnemonic" / "state.sqlite")
    Base.metadata.create_all(engine)
    return engine


def test_first_scan_classifies_new_and_stores_hashes(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(
        vault, "nash", "What is a {{c1::Nash equilibrium}}? It is {{c2::a stable solution}}."
    )
    engine = _engine(vault)

    report = ReconciliationService(vault, engine).run()

    assert report.counts["new"] == 1
    with session_scope(engine) as s:
        rows = s.query(SchedulingState).all()
        assert len(rows) == 1
        assert rows[0].core_hash is not None
        assert rows[0].cloze_signature is not None
        assert bool(rows[0].core_changed) is False
        logs = s.query(CoreChangeLog).all()
        assert len(logs) == 1 and logs[0].change_kind == "new"


def test_rescan_with_no_edit_is_unchanged(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "nash", "What is a {{c1::Nash equilibrium}}?")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()

    report = ReconciliationService(vault, engine).run()

    assert report.counts["unchanged"] == 1
    with session_scope(engine) as s:
        assert s.query(CoreChangeLog).count() == 1  # no new audit row on rescan


def test_trivial_edit_does_not_flag_or_invalidate(tmp_path: Path):
    vault = _vault(tmp_path)
    path = _write_card(vault, "nash", "What is a {{c1::Nash equilibrium}}?")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()
    card_id = _only_card_id(engine)
    _seed_variation(engine, card_id)

    # whitespace-only edit (block ID is preserved by the scanner)
    path.write_text(path.read_text().replace("What is a", "What  is   a"))
    report = ReconciliationService(vault, engine).run()

    assert report.counts["trivial"] == 1
    with session_scope(engine) as s:
        assert bool(s.get(SchedulingState, card_id).core_changed) is False
        assert s.query(VariationMeta).one().invalidated_at is None


def test_material_edit_flags_and_invalidates(tmp_path: Path):
    vault = _vault(tmp_path)
    path = _write_card(vault, "nash", "What is a {{c1::Nash equilibrium}}?")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()
    card_id = _only_card_id(engine)
    _seed_variation(engine, card_id)
    _seed_training(engine, card_id)
    _set_fsrs(engine, card_id, stability=42.0, reps=9)

    # Material edit: change punctuation (affects core hash but not cloze structure)
    path.write_text(
        path.read_text().replace("{{c1::Nash equilibrium}}?", "{{c1::Nash equilibrium}}.")
    )
    report = ReconciliationService(vault, engine).run()

    assert report.counts["material"] == 1
    with session_scope(engine) as s:
        row = s.get(SchedulingState, card_id)
        assert bool(row.core_changed) is True
        assert row.core_changed_at is not None
        assert row.stability == 42.0 and row.reps == 9  # FSRS untouched
        assert s.query(VariationMeta).one().invalidated_at is not None
        assert s.query(TrainingExample).one().invalidated_at is not None
        kinds = {log.change_kind for log in s.query(CoreChangeLog).all()}
        assert "material" in kinds


def test_dangling_parent_marks_child_orphan(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "child", "A {{c1::child}} card.")
    engine = _engine(vault)
    ReconciliationService(vault, engine).run()
    card_id = _only_card_id(engine)
    with session_scope(engine) as s:
        s.get(SchedulingState, card_id).parent_card_id = "card-deadparent"

    report = ReconciliationService(vault, engine).run()

    assert report.dangling.parents == [card_id]
    with session_scope(engine) as s:
        assert bool(s.get(SchedulingState, card_id).orphan) is True


def test_duplicate_cards_detected(tmp_path: Path):
    vault = _vault(tmp_path)
    _write_card(vault, "a", "The {{c1::capital}} of France is {{c2::Paris}}.")
    _write_card(vault, "b", "the {{c1::capital}} of france is {{c2::paris}}.")
    engine = _engine(vault)

    report = ReconciliationService(vault, engine).run()

    assert len(report.duplicates) == 1
    assert len(report.duplicates[0].card_ids) == 2


# --- helpers ---


def _only_card_id(engine) -> str:
    with session_scope(engine) as s:
        return s.query(SchedulingState).one().card_id


def _set_fsrs(engine, card_id: str, *, stability: float, reps: int) -> None:
    with session_scope(engine) as s:
        row = s.get(SchedulingState, card_id)
        row.stability = stability
        row.reps = reps


def _seed_variation(engine, card_id: str) -> None:
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id=f"var-{card_id}",
                card_id=card_id,
                strategy="rephrase",
                model="m",
                generated_at=datetime(2026, 6, 1),
                content_hash="ch",
                note_path="p.qmd",
            )
        )


def _seed_training(engine, card_id: str) -> None:
    with session_scope(engine) as s:
        s.add(
            TrainingExample(
                id=f"te-{card_id}",
                card_id=card_id,
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=1,
                created_at=datetime(2026, 6, 1),
            )
        )
