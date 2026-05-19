# Database Migrations

Mnemonic uses [Alembic](https://alembic.sqlalchemy.org/) to version the SQLite
sidecar that lives at `<vault>/.mnemonic/state.sqlite`. The sidecar holds
application state only — FSRS scheduling, review history, variation metadata,
LLM usage. Card and deck *content* lives in vault notes on disk and is not
versioned by Alembic.

## Layout

- **Config**: `backend/alembic/alembic.ini`, `backend/alembic/env.py`
- **Versions**: `backend/alembic/versions/`
- **Connection URL**: derived at runtime from `mnemonic.config.load_config()`
  → `sqlite:///<vault_path>/.mnemonic/state.sqlite`. There is no environment
  variable to override; the vault path comes from `~/.config/mnemonic/config.toml`.

## Tables tracked

- `scheduling_state` — one row per card-block-id; FSRS stability, difficulty,
  reps, lapses, due date, leech score, suspended flag, orphan flag
- `review_log` — append-only per-review record with before/after FSRS values
- `variation_meta` — metadata for each LLM-generated variation; the variation
  *text* lives in the note's `## Variations` section, not here
- `llm_usage` — per-call telemetry (tokens, cache hits, cost in millicents)
- `training_example` — labelled (q, a) pairs for offline DSPy optimisation

## Workflow

### Apply migrations

```bash
cd backend
uv run alembic upgrade head
```

Run on first use, after pulling a new revision, or after cloning a vault that
doesn't yet have `state.sqlite`. Idempotent: re-running on an up-to-date
database is a no-op.

### Check state

```bash
uv run alembic current      # current revision id
uv run alembic history      # full revision chain
```

### Roll back

```bash
uv run alembic downgrade -1            # one step
uv run alembic downgrade <revision>    # specific revision
uv run alembic downgrade base          # drop all tables
```

Because the SQLite file is committed to the vault Git repo (binary, with
`-merge` set via `.gitattributes`), the most common "rollback" is actually
`git checkout` of a previous vault commit — which restores both schema and
data atomically. Use `alembic downgrade` for development-time schema changes,
not for recovering production state.

### Create a new migration

After editing models in `src/mnemonic/db/models/`:

```bash
uv run alembic revision --autogenerate -m "describe the change"
```

Alembic compares `Base.metadata` against the live `state.sqlite` and emits
SQL into a new file under `alembic/versions/`. Review the generated migration
— autogenerate cannot detect column renames or data migrations.

For data-only or hand-crafted changes:

```bash
uv run alembic revision -m "describe the change"
```

This emits an empty migration template.

## Conventions

- Filename prefix `vault_storage_NNNN_…` for migrations added during or after
  the vault-storage rewrite. The legacy `0001_initial_*` and `0002_seed_*`
  filenames were deleted along with the PostgreSQL models in that rewrite.
- `revision`/`down_revision` chain unbroken; do not rebase migrations after
  they have been published to any committed vault.
- Use SQLite-safe ops (`render_as_batch=True` is set in `env.py` — needed for
  most `ALTER TABLE` operations).
- Schema changes that affect existing users' vaults should ship with a
  one-shot migration script under `backend/scripts/` if the migration is
  non-trivial.

## Anatomy of a migration

```python
"""describe the change

Revision ID: vault_storage_0002_add_due_index
Revises: vault_storage_0001_initial_sqlite_schema
Create Date: 2026-05-19
"""

from alembic import op
import sqlalchemy as sa

revision = "vault_storage_0002_add_due_index"
down_revision = "vault_storage_0001_initial_sqlite_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_scheduling_due_state",
        "scheduling_state",
        ["due", "state"],
    )


def downgrade() -> None:
    op.drop_index("idx_scheduling_due_state", table_name="scheduling_state")
```

## Troubleshooting

### "Vault not configured"

`alembic` raises `VaultNotConfiguredError` if `~/.config/mnemonic/config.toml`
is missing or has no `[vault] path`. Create the config first (see the backend
README).

### "Multiple head revisions"

Caused by two migrations sharing the same `down_revision`. Use
`uv run alembic heads` to list, then merge:

```bash
uv run alembic merge -m "merge heads" <head_a> <head_b>
```

### "Cannot detect column rename"

Alembic autogenerate sees rename as drop+add. Edit the generated migration to
use `op.alter_column(..., new_column_name=...)`.

## Further reading

- [Alembic documentation](https://alembic.sqlalchemy.org/)
- [SQLAlchemy 2.0 ORM](https://docs.sqlalchemy.org/en/20/orm/)
- The storage spec at
  `docs/superpowers/specs/2026-05-10-vault-storage-design.md` — section 5
  for the full schema rationale.
