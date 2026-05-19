"""Tests for SQLite engine factory and session helpers."""

from pathlib import Path

from sqlalchemy import text

from mnemonic.db.sqlite import create_engine, session_scope


def test_engine_creates_file(tmp_path: Path):
    """Engine should create a SQLite database file at the specified path."""
    db_path = tmp_path / "state.sqlite"
    engine = create_engine(db_path)
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    assert db_path.exists()


def test_session_scope_commits(tmp_path: Path):
    """Session scope should commit on successful context exit."""
    db_path = tmp_path / "state.sqlite"
    engine = create_engine(db_path)

    # Create a test table
    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE t (k TEXT PRIMARY KEY, v TEXT)"))

    # Insert via session scope (should commit)
    with session_scope(engine) as s:
        s.execute(text("INSERT INTO t VALUES ('a', 'b')"))

    # Verify the row persists (committed)
    with engine.connect() as conn:
        rows = list(conn.execute(text("SELECT * FROM t")))

    assert len(rows) == 1
    assert rows[0][0] == "a"
    assert rows[0][1] == "b"
