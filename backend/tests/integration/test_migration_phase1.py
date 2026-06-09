"""Integration test: verify phase 1 Alembic migration upgrade + downgrade.

Runs both migrations against a throwaway SQLite file — never touches the
user's real vault database.
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

VERSIONS_DIR = (
    Path(__file__).parent.parent.parent / "alembic" / "versions"
)
REV1_PATH = VERSIONS_DIR / "vault_storage_0001_initial_sqlite_schema.py"
REV2_PATH = VERSIONS_DIR / "prompt_opt_0002_phase1_attribution.py"
THROWAWAY_DB = "/tmp/mnemonic_mig_check.sqlite"


def _load_module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)  # type: ignore[arg-type]
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


@pytest.fixture()
def throwaway_engine():
    """Yield a fresh SQLite engine at a known temp path; remove it afterward."""
    db_path = THROWAWAY_DB
    if os.path.exists(db_path):
        os.remove(db_path)
    engine = sa.create_engine(f"sqlite:///{db_path}", echo=False)
    yield engine
    engine.dispose()
    if os.path.exists(db_path):
        os.remove(db_path)


def _table_names(conn) -> set[str]:
    return set(sa.inspect(conn).get_table_names())


def _column_names(conn, table: str) -> set[str]:
    return {c["name"] for c in sa.inspect(conn).get_columns(table)}


def test_migration_upgrade_and_downgrade(throwaway_engine):
    rev1 = _load_module(REV1_PATH, "rev1")
    rev2 = _load_module(REV2_PATH, "rev2")

    with throwaway_engine.connect() as conn:
        ctx = MigrationContext.configure(conn, opts={"render_as_batch": True})
        with Operations.context(ctx):
            # ── upgrade ──────────────────────────────────────────────────────
            rev1.upgrade()
            rev2.upgrade()
            conn.commit()

            tables = _table_names(conn)

            # prompt_version table created
            assert "prompt_version" in tables, "prompt_version table missing after upgrade"

            # training_example gained four new columns
            te_cols = _column_names(conn, "training_example")
            for col in ("prompt_version_id", "reward", "maturity", "finalized"):
                assert col in te_cols, f"training_example.{col} missing after upgrade"

            # variation_meta gained two new columns
            vm_cols = _column_names(conn, "variation_meta")
            for col in ("prompt_version_id", "arm"):
                assert col in vm_cols, f"variation_meta.{col} missing after upgrade"

            # ── downgrade ────────────────────────────────────────────────────
            rev2.downgrade()
            conn.commit()

            tables_after = _table_names(conn)

            # prompt_version table dropped
            assert "prompt_version" not in tables_after, (
                "prompt_version table still present after downgrade"
            )

            # attribution columns removed from training_example
            te_cols_after = _column_names(conn, "training_example")
            for col in ("prompt_version_id", "reward", "maturity", "finalized"):
                assert col not in te_cols_after, (
                    f"training_example.{col} still present after downgrade"
                )

            # attribution columns removed from variation_meta
            vm_cols_after = _column_names(conn, "variation_meta")
            for col in ("prompt_version_id", "arm"):
                assert col not in vm_cols_after, (
                    f"variation_meta.{col} still present after downgrade"
                )
