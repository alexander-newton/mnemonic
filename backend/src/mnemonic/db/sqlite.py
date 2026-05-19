"""SQLite engine factory and session helper for Mnemonic state."""

from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from sqlalchemy import Engine, event
from sqlalchemy import create_engine as _create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_engine(db_path: Path) -> Engine:
    """Create a SQLite engine targeting the given path.

    Enables WAL mode for concurrent access and foreign keys for referential integrity.

    Args:
        db_path: Path to the SQLite database file. Parent directories are created if needed.

    Returns:
        A SQLAlchemy Engine configured for SQLite with WAL and foreign key pragmas.
    """
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = _create_engine(
        f"sqlite:///{db_path}",
        future=True,
        connect_args={"check_same_thread": False},
    )

    @event.listens_for(engine, "connect")
    def _set_pragmas(dbapi_conn, _):
        """Set SQLite pragmas on each connection: WAL mode and foreign keys."""
        cur = dbapi_conn.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()

    return engine


@contextmanager
def session_scope(engine: Engine) -> Iterator[Session]:
    """Provide a transactional scope around a series of operations.

    Commits on successful exit, rolls back on exception.

    Args:
        engine: SQLAlchemy Engine.

    Yields:
        A SQLAlchemy Session.

    Raises:
        Any exception raised within the context is re-raised after rollback.
    """
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False, future=True)
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
