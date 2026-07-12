"""Round-trip test for ReviewLog.deck_folder."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from mnemonic.db.models import Base, ReviewLog
from mnemonic.db.sqlite import create_engine, session_scope


def test_reviewlog_deck_folder_roundtrip(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            ReviewLog(
                id="r1", card_id="card-a", rating=3, response_time_ms=1000,
                review_time=datetime(2026, 7, 10, 9, 0, 0), deck_folder="gt",
            )
        )
    with session_scope(engine) as s:
        assert s.get(ReviewLog, "r1").deck_folder == "gt"


def test_reviewlog_deck_folder_defaults_none(tmp_path: Path):
    engine = create_engine(tmp_path / "s.sqlite")
    Base.metadata.create_all(engine)
    with session_scope(engine) as s:
        s.add(
            ReviewLog(
                id="r2", card_id="card-b", rating=1, response_time_ms=500,
                review_time=datetime(2026, 7, 10, 9, 0, 0),
            )
        )
    with session_scope(engine) as s:
        assert s.get(ReviewLog, "r2").deck_folder is None
