"""Integration tests for database migrations.

Tests the Alembic migration infrastructure, including:
- Upgrading from base to head
- Downgrading migrations
- Idempotency of migrations
- Presence of all expected tables and constraints
- Seeding of builtin card types
"""

import os
from typing import Generator

import pytest
from alembic.config import Config
from alembic import command
from sqlalchemy import (
    create_engine,
    inspect,
    text,
    Column,
    String,
    Integer,
)
from sqlalchemy.orm import Session, sessionmaker


@pytest.fixture
def test_database_url() -> str:
    """Get test database URL from environment or use a default."""
    # For testing, use a dedicated test database
    url = os.getenv("TEST_DATABASE_URL")
    if url:
        return url
    # Default to SQLite in-memory for testing if no PostgreSQL available
    return "sqlite:///:memory:"


@pytest.fixture
def alembic_config() -> Config:
    """Create an Alembic configuration for testing."""
    config = Config("/home/alexander/Documents/claude-mnemonic/backend/alembic/alembic.ini")
    config.set_main_option(
        "script_location",
        "/home/alexander/Documents/claude-mnemonic/backend/alembic",
    )
    return config


@pytest.fixture
def test_db_engine(test_database_url: str):
    """Create a test database engine."""
    engine = create_engine(test_database_url, echo=False)
    return engine


@pytest.fixture
def migrate_db(alembic_config: Config, test_database_url: str) -> Generator:
    """Fixture that sets up and tears down test database with migrations."""
    # Set the database URL
    alembic_config.set_main_option("sqlalchemy.url", test_database_url)

    # Upgrade to head
    command.upgrade(alembic_config, "head")

    yield alembic_config

    # Downgrade to base for cleanup
    try:
        command.downgrade(alembic_config, "base")
    except NotImplementedError:
        # Some databases may not support downgrading
        pytest.skip("Database does not support downgrade operations")
    except Exception as e:
        # Log unexpected failures during cleanup
        pytest.fail(f"Unexpected error during downgrade cleanup: {e}")


@pytest.mark.integration
class TestMigrations:
    """Test database migrations."""

    def test_upgrade_to_head(self, migrate_db: Config) -> None:
        """Test that we can upgrade from base to head."""
        # This is implicitly tested by the migrate_db fixture
        # If we got here without exception, upgrade succeeded
        assert True

    def test_all_tables_exist(self, test_db_engine, migrate_db: Config) -> None:
        """Test that all expected tables exist after migration."""
        inspector = inspect(test_db_engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "user",
            "card_type",
            "deck",
            "card",
            "review_log",
            "variation_cache",
            "training_example",
            "llm_usage",
        ]

        for table in expected_tables:
            assert (
                table in tables
            ), f"Table '{table}' not found in database. Found: {tables}"

    def test_user_table_structure(self, test_db_engine, migrate_db: Config) -> None:
        """Test that user table has correct columns and constraints."""
        inspector = inspect(test_db_engine)

        columns = {col["name"]: col for col in inspector.get_columns("user")}

        expected_columns = [
            "id",
            "email",
            "password_hash",
            "fsrs_params",
            "settings",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in user table"

        # Check that email is unique
        constraints = inspector.get_unique_constraints("user")
        email_unique = any("email" in constraint["column_names"] for constraint in constraints)
        assert email_unique, "Email should have unique constraint"

    def test_card_type_table_structure(
        self, test_db_engine, migrate_db: Config
    ) -> None:
        """Test that card_type table has correct columns and constraints."""
        inspector = inspect(test_db_engine)

        columns = {col["name"]: col for col in inspector.get_columns("card_type")}

        expected_columns = [
            "id",
            "user_id",
            "name",
            "description",
            "parent_type_id",
            "syntax_type",
            "fields",
            "render_pipeline",
            "is_builtin",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in card_type table"

    def test_card_table_structure(self, test_db_engine, migrate_db: Config) -> None:
        """Test that card table has correct columns."""
        inspector = inspect(test_db_engine)

        columns = {col["name"]: col for col in inspector.get_columns("card")}

        expected_columns = [
            "id",
            "deck_id",
            "card_type_id",
            "content",
            "notes",
            "tags",
            "state",
            "stability",
            "difficulty",
            "due",
            "reps",
            "lapses",
            "leech_score",
            "leech_notified",
            "parent_card_id",
            "suspended",
            "created_at",
            "updated_at",
        ]

        for col in expected_columns:
            assert col in columns, f"Column '{col}' not found in card table"

    def test_foreign_keys_exist(self, test_db_engine, migrate_db: Config) -> None:
        """Test that foreign key relationships are properly configured."""
        inspector = inspect(test_db_engine)

        # Check deck -> user FK
        deck_fks = inspector.get_foreign_keys("deck")
        assert any(
            fk["constrained_columns"] == ["user_id"] for fk in deck_fks
        ), "deck should have FK to user"

        # Check card -> deck and card -> card_type FKs
        card_fks = inspector.get_foreign_keys("card")
        fk_cols = [fk["constrained_columns"][0] for fk in card_fks]
        assert "deck_id" in fk_cols, "card should have FK to deck"
        assert "card_type_id" in fk_cols, "card should have FK to card_type"

    def test_builtin_card_types_seeded(
        self, test_db_engine, migrate_db: Config
    ) -> None:
        """Test that builtin card types are seeded after migration."""
        engine = create_engine(
            migrate_db.get_main_option("sqlalchemy.url"), echo=False
        )
        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Query for builtin card types
            result = session.execute(
                text(
                    """
                    SELECT id, name, syntax_type, is_builtin, user_id
                    FROM card_type
                    WHERE is_builtin = TRUE AND user_id IS NULL
                    ORDER BY name
                    """
                )
            )

            builtin_types = result.fetchall()

            assert len(builtin_types) >= 4, f"Expected at least 4 builtin card types, got {len(builtin_types)}"

            # Check for expected types
            type_names = {row[1] for row in builtin_types}
            expected_names = {"Basic", "BasicReversed", "Cloze", "ImageCloze"}

            for expected in expected_names:
                assert (
                    expected in type_names
                ), f"Expected builtin card type '{expected}' not found"

        finally:
            session.close()

    def test_downgrade_from_head(self, alembic_config: Config, test_database_url: str) -> None:
        """Test that migrations can be downgraded."""
        alembic_config.set_main_option("sqlalchemy.url", test_database_url)

        # Upgrade first
        command.upgrade(alembic_config, "head")

        # Now downgrade to base
        try:
            command.downgrade(alembic_config, "base")

            # Verify tables are gone
            engine = create_engine(test_database_url, echo=False)
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            assert len(tables) == 0, f"Expected no tables after downgrade, found: {tables}"
        except NotImplementedError:
            # Some databases may not support downgrade
            pytest.skip("Database does not support downgrade")
        finally:
            engine.dispose()

    def test_upgrade_is_idempotent(
        self, alembic_config: Config, test_database_url: str
    ) -> None:
        """Test that upgrading multiple times is safe."""
        alembic_config.set_main_option("sqlalchemy.url", test_database_url)

        # Upgrade to head multiple times
        command.upgrade(alembic_config, "head")
        command.upgrade(alembic_config, "head")
        command.upgrade(alembic_config, "head")

        # Verify tables still exist and are correct
        engine = create_engine(test_database_url, echo=False)
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = [
            "user",
            "card_type",
            "deck",
            "card",
            "review_log",
            "variation_cache",
            "training_example",
            "llm_usage",
        ]

        for table in expected_tables:
            assert table in tables, f"Table '{table}' missing after idempotent upgrade"

        engine.dispose()

    def test_indexes_created(self, test_db_engine, migrate_db: Config) -> None:
        """Test that expected indexes are created."""
        inspector = inspect(test_db_engine)

        # Check user indexes
        user_indexes = inspector.get_indexes("user")
        assert any(
            "email" in idx["column_names"] for idx in user_indexes
        ), "user table should have email index"

        # Check deck indexes
        deck_indexes = inspector.get_indexes("deck")
        assert any(
            "user_id" in idx["column_names"] for idx in deck_indexes
        ), "deck table should have user_id index"

        # Check card indexes
        card_indexes = inspector.get_indexes("card")
        assert any(
            "deck_id" in idx["column_names"] for idx in card_indexes
        ), "card table should have deck_id index"
        assert any(
            "card_type_id" in idx["column_names"] for idx in card_indexes
        ), "card table should have card_type_id index"
