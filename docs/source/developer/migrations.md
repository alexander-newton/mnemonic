# Database Migrations

Mnemonic uses [Alembic](https://alembic.sqlalchemy.org/) for database schema versioning and migrations. This document explains how to work with migrations.

## Overview

- **Location**: `backend/alembic/`
- **Configuration**: `alembic.ini`, `env.py`
- **Migration Scripts**: `alembic/versions/`

All database schema changes must be tracked as migrations to ensure:
1. **Reproducibility**: Database can be rebuilt from scratch
2. **Version Control**: Schema changes are documented with git
3. **Deployment Safety**: Migrations can be applied/rolled back on production databases

## Current Migrations

### 0001 - Initial Schema with All Models

Creates all core tables and relationships:
- `user` - User accounts and FSRS parameters
- `deck` - Card collections with configuration
- `card_type` - Card format templates
- `card` - Individual flashcards
- `review_log` - Review history with FSRS state changes
- `variation_cache` - Cached question variations
- `training_example` - Training data for LLM prompt optimization
- `llm_usage` - Token and cost tracking for LLM API usage

### 0002 - Seed Builtin Card Types

Inserts the four builtin card types:
- **Basic**: Front/back flashcard (frontback syntax)
- **BasicReversed**: Front/back with automatic reverse (frontback syntax)
- **Cloze**: Cloze deletion cards (cloze syntax)
- **ImageCloze**: Image cloze with region highlighting (image_cloze syntax)

## Running Migrations

### Apply All Migrations

```bash
cd backend
uv run alembic upgrade head
```

This upgrades the database to the latest migration version.

### Apply Specific Migration

```bash
uv run alembic upgrade 0002
```

### Check Current Version

```bash
uv run alembic current
```

Output: `0002_seed_builtin_card_types`

### View Migration History

```bash
uv run alembic history
```

Shows all applied and pending migrations.

## Rollback Migrations

### Rollback One Step

```bash
uv run alembic downgrade -1
```

Rolls back the last applied migration.

### Rollback to Specific Version

```bash
uv run alembic downgrade 0001
```

### Rollback All Migrations

```bash
uv run alembic downgrade base
```

This removes all tables and returns the database to a clean state.

## Creating New Migrations

### Automatic Migration Generation (Recommended)

After modifying SQLAlchemy models in `backend/src/mnemonic/db/models/`, generate a migration automatically:

```bash
cd backend
uv run alembic revision --autogenerate -m "your migration message"
```

Alembic will:
1. Compare the current database schema with your models
2. Generate SQL for creating/modifying tables and constraints
3. Create a new migration file in `alembic/versions/`

**Important**: Always review the generated migration! Alembic cannot detect all schema changes (like renaming columns).

### Manual Migration Creation

For complex changes or data migrations, create a migration manually:

```bash
uv run alembic revision -m "your migration message"
```

This creates an empty migration template. Edit `alembic/versions/<revision>_<slug>.py` to add your SQL operations.

## Migration Structure

A typical migration file looks like:

```python
"""Add user_id column to decks table

Revision ID: 0003
Revises: 0002
Create Date: 2025-02-03 14:30:00

"""
from alembic import op
import sqlalchemy as sa

revision = "0003"
down_revision = "0002"

def upgrade() -> None:
    """Apply the migration."""
    op.add_column('deck', sa.Column('user_id', sa.UUID, nullable=False))
    op.create_foreign_key('fk_deck_user_id', 'deck', 'user', ['user_id'], ['id'])

def downgrade() -> None:
    """Revert the migration."""
    op.drop_constraint('fk_deck_user_id', 'deck', type_='foreignkey')
    op.drop_column('deck', 'user_id')
```

### Key Concepts

- **upgrade()**: Operations to apply the migration (usually called when running `alembic upgrade`)
- **downgrade()**: Operations to revert the migration (called when running `alembic downgrade`)
- **revision**: Unique identifier for this migration
- **down_revision**: The migration this one depends on (forms a chain)

## Best Practices

### 1. Test Migrations Locally

Always test migrations on your local database before committing:

```bash
# Upgrade to head
uv run alembic upgrade head

# Verify the schema looks correct
psql mnemonic -c "\dt+"

# Test rollback
uv run alembic downgrade -1

# Re-upgrade
uv run alembic upgrade head
```

### 2. Use Descriptive Messages

Migration messages should describe what changed:

```bash
# Good
uv run alembic revision --autogenerate -m "Add user_id to card table"

# Bad
uv run alembic revision --autogenerate -m "Update schema"
```

### 3. Separate Data and Schema Changes

Keep data migrations separate from schema migrations for clarity:

```bash
# Schema change
uv run alembic revision --autogenerate -m "Add status column to cards"

# Data migration
uv run alembic revision -m "Populate status from state enum"
```

### 4. Ensure Migrations Are Reversible

All migrations should be reversible (unless explicitly documented as one-way):

```python
def downgrade() -> None:
    # This should undo everything in upgrade()
    op.drop_column('card', 'status')
```

### 5. Don't Skip Constraints

Always create:
- **Primary keys** for new tables
- **Foreign keys** for relationships
- **Indexes** for frequently queried columns
- **Unique constraints** for unique fields
- **NOT NULL constraints** where appropriate

## Common Operations

### Add a Column

```python
op.add_column('card', sa.Column('status', sa.String(50), nullable=False))
```

### Drop a Column

```python
op.drop_column('card', 'status')
```

### Create an Index

```python
op.create_index('ix_card_created_at', 'card', ['created_at'])
```

### Add a Foreign Key

```python
op.create_foreign_key('fk_card_deck', 'card', 'deck', ['deck_id'], ['id'], ondelete='CASCADE')
```

### Rename a Column

```python
op.alter_column('card', 'old_name', new_column_name='new_name')
```

## Configuration

### alembic/alembic.ini

Main configuration file:

```ini
[alembic]
script_location = alembic
sqlalchemy.url = driver://user:password@localhost/dbname
```

The `sqlalchemy.url` can be overridden with the `DATABASE_URL` environment variable:

```bash
DATABASE_URL="postgresql://user:pass@prod-db:5432/mnemonic" \
  uv run alembic upgrade head
```

### alembic/env.py

Python configuration file that:
- Imports database models from `mnemonic.db.models`
- Sets `target_metadata` for autogenerate
- Configures offline vs online migrations
- Handles database connection

## Troubleshooting

### "No migration target specified"

You need to specify where to upgrade/downgrade to:

```bash
uv run alembic upgrade head  # Go to latest
uv run alembic upgrade 0002  # Go to specific version
```

### "Can't connect to database"

If the database is not running, migrations will fail. Start your database:

```bash
docker-compose -f infrastructure/docker-compose.dev.yml up postgres
```

Or configure a test database:

```bash
DATABASE_URL="sqlite:///./test.db" uv run alembic upgrade head
```

### "alembic: error: No module named 'mnemonic'"

The Alembic environment needs the mnemonic package in the Python path. Ensure you're using:

```bash
uv run alembic ...  # Correct - uses venv
python -m alembic ...  # Wrong - may use wrong Python
```

## Further Reading

- [Alembic Official Docs](https://alembic.sqlalchemy.org/)
- [SQLAlchemy ORM Documentation](https://docs.sqlalchemy.org/en/20/orm/)
- [Mnemonic Database Models](../../api/db/models.md)
