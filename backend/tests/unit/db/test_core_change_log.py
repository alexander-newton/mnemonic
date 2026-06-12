"""Round-trip tests for integrity columns and the CoreChangeLog table."""

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


def test_scheduling_state_integrity_columns(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            SchedulingState(
                card_id="card-aaaabbbb",
                core_hash="raw",
                core_hash_normalized="norm",
                cloze_signature="cl",
                core_changed=True,
                core_changed_at=datetime(2026, 6, 11, 9, 0, 0),
            )
        )
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.core_hash == "raw"
        assert row.core_hash_normalized == "norm"
        assert row.cloze_signature == "cl"
        assert bool(row.core_changed) is True


def test_scheduling_state_integrity_columns_default_none(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(SchedulingState(card_id="card-ccccdddd"))
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-ccccdddd")
        assert row.core_hash is None
        assert bool(row.core_changed) is False


def test_variation_and_training_invalidated_at(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    when = datetime(2026, 6, 11, 9, 0, 0)
    with session_scope(engine) as s:
        s.add(
            VariationMeta(
                id="v1",
                card_id="card-aaaabbbb",
                strategy="rephrase",
                model="m",
                generated_at=when,
                content_hash="ch",
                note_path="p.qmd",
                invalidated_at=when,
            )
        )
        s.add(
            TrainingExample(
                id="te1",
                card_id="card-aaaabbbb",
                base_q="bq",
                base_a="ba",
                variation_q="vq",
                variation_a="va",
                label=1,
                created_at=when,
                invalidated_at=when,
            )
        )
    with session_scope(engine) as s:
        assert s.get(VariationMeta, "v1").invalidated_at == when
        assert s.get(TrainingExample, "te1").invalidated_at == when


def test_core_change_log_round_trip(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    when = datetime(2026, 6, 11, 9, 0, 0)
    with session_scope(engine) as s:
        s.add(
            CoreChangeLog(
                id="log1",
                card_id="card-aaaabbbb",
                change_kind="material",
                old_hash="old",
                new_hash="new",
                old_normalized="oldn",
                new_normalized="newn",
                detected_at=when,
            )
        )
    with session_scope(engine) as s:
        row = s.get(CoreChangeLog, "log1")
        assert row.change_kind == "material"
        assert row.old_hash == "old"
        assert row.new_hash == "new"
        assert row.detected_at == when
