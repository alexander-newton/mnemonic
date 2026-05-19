from datetime import datetime
from pathlib import Path
from mnemonic.db.sqlite import create_engine, session_scope
from mnemonic.db.models import Base, SchedulingState, ReviewLog, VariationMeta, LLMUsage, TrainingExample


def test_scheduling_state_round_trip(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(SchedulingState(
            card_id="card-aaaabbbb",
            state="new",
            stability=0.0,
            difficulty=5.0,
            reps=0,
            lapses=0,
            leech_score=0.0,
        ))
    with session_scope(engine) as s:
        row = s.get(SchedulingState, "card-aaaabbbb")
        assert row.state == "new"
        assert row.stability == 0.0


def test_review_log_no_user_id(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(ReviewLog(
            id="r1",
            card_id="card-aaaabbbb",
            rating=3,
            response_time_ms=1200,
            review_time=datetime(2026, 5, 10, 12, 0, 0),
        ))
    with session_scope(engine) as s:
        row = s.get(ReviewLog, "r1")
        assert row.rating == 3
        assert not hasattr(row, "user_id")


def test_variation_meta_minimal(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(VariationMeta(
            id="v1",
            card_id="card-aaaabbbb",
            strategy="rephrase",
            model="claude-haiku-4-5",
            generated_at=datetime(2026, 5, 10),
            content_hash="abc",
            note_path="01_Projects/x.qmd",
        ))
    with session_scope(engine) as s:
        row = s.get(VariationMeta, "v1")
        assert row.strategy == "rephrase"
        assert row.shown_count == 0
