"""Initial schema with all models

Revision ID: 0001
Revises:
Create Date: 2025-02-03 14:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create user table first (no dependencies)
    op.create_table(
        "user",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.Text(), nullable=False),
        sa.Column("fsrs_params", postgresql.JSON(), nullable=False),
        sa.Column("settings", postgresql.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index(op.f("ix_user_email"), "user", ["email"], unique=True)

    # Create card_type table (depends on user for FK, but user_id is nullable)
    op.create_table(
        "card_type",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("parent_type_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column(
            "syntax_type",
            postgresql.ENUM(
                "frontback", "cloze", "image_cloze", "custom", name="syntaxtype"
            ),
            nullable=False,
        ),
        sa.Column("fields", postgresql.JSON(), nullable=False),
        sa.Column("render_pipeline", postgresql.JSON(), nullable=False),
        sa.Column("is_builtin", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["parent_type_id"], ["card_type.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_card_type_user_id"), "card_type", ["user_id"])

    # Create deck table (depends on user)
    op.create_table(
        "deck",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("variation_enabled", sa.Boolean(), nullable=False),
        sa.Column("variation_frequency", sa.Float(), nullable=False),
        sa.Column("leech_threshold", sa.Integer(), nullable=False),
        sa.Column("daily_review_limit", sa.Integer(), nullable=True),
        sa.Column("daily_new_limit", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_deck_user_id"), "deck", ["user_id"])

    # Create card table (depends on deck and card_type)
    op.create_table(
        "card",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("deck_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_type_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("tags", postgresql.JSON(), nullable=False),
        sa.Column(
            "state",
            postgresql.ENUM("new", "learning", "review", "relearning", name="cardstate"),
            nullable=False,
        ),
        sa.Column("stability", sa.Float(), nullable=False),
        sa.Column("difficulty", sa.Float(), nullable=False),
        sa.Column("due", sa.DateTime(timezone=False), nullable=True),
        sa.Column("reps", sa.Integer(), nullable=False),
        sa.Column("lapses", sa.Integer(), nullable=False),
        sa.Column("leech_score", sa.Float(), nullable=False),
        sa.Column("leech_notified", sa.Boolean(), nullable=False),
        sa.Column("parent_card_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("suspended", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["card_type_id"], ["card_type.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["deck_id"], ["deck.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["parent_card_id"], ["card.id"], ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_card_card_type_id"), "card", ["card_type_id"])
    op.create_index(op.f("ix_card_deck_id"), "card", ["deck_id"])

    # Create review_log table (depends on card and user)
    op.create_table(
        "review_log",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("response_time_ms", sa.Integer(), nullable=False),
        sa.Column("review_time", sa.DateTime(timezone=False), nullable=False),
        sa.Column(
            "state_before",
            postgresql.ENUM(
                "new", "learning", "review", "relearning", name="cardstate"
            ),
            nullable=True,
        ),
        sa.Column(
            "state_after",
            postgresql.ENUM(
                "new", "learning", "review", "relearning", name="cardstate"
            ),
            nullable=True,
        ),
        sa.Column("stability_before", sa.Float(), nullable=True),
        sa.Column("stability_after", sa.Float(), nullable=True),
        sa.Column("difficulty_before", sa.Float(), nullable=True),
        sa.Column("difficulty_after", sa.Float(), nullable=True),
        sa.Column("variation_used", sa.Boolean(), nullable=False),
        sa.Column("variation_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("variation_helpful", sa.Boolean(), nullable=True),
        sa.ForeignKeyConstraint(["card_id"], ["card.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_review_log_card_id"), "review_log", ["card_id"])
    op.create_index(op.f("ix_review_log_user_id"), "review_log", ["user_id"])

    # Create variation_cache table (depends on card)
    op.create_table(
        "variation_cache",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("varied_content", sa.Text(), nullable=False),
        sa.Column("model_used", sa.String(255), nullable=False),
        sa.Column("prompt_version", sa.String(255), nullable=True),
        sa.Column("semantic_similarity", sa.Float(), nullable=True),
        sa.Column("lexical_difference", sa.Float(), nullable=True),
        sa.Column("times_shown", sa.Integer(), nullable=False),
        sa.Column("times_correct", sa.Integer(), nullable=False),
        sa.Column("user_ratings", postgresql.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["card_id"], ["card.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_variation_cache_card_id"), "variation_cache", ["card_id"])

    # Create training_example table (depends on card)
    op.create_table(
        "training_example",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("card_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("original_content", sa.Text(), nullable=False),
        sa.Column("varied_content", sa.Text(), nullable=False),
        sa.Column("user_feedback", postgresql.JSON(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=False),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["card_id"], ["card.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_training_example_card_id"), "training_example", ["card_id"])

    # Create llm_usage table (depends on user)
    op.create_table(
        "llm_usage",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("model", sa.String(255), nullable=False),
        sa.Column("tokens_in", sa.Integer(), nullable=False),
        sa.Column("tokens_out", sa.Integer(), nullable=False),
        sa.Column("cost_usd", sa.Numeric(precision=10, scale=4), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_llm_usage_date"), "llm_usage", ["date"])
    op.create_index(op.f("ix_llm_usage_user_id"), "llm_usage", ["user_id"])


def downgrade() -> None:
    # Drop all tables in reverse order
    op.drop_index(op.f("ix_llm_usage_user_id"), table_name="llm_usage")
    op.drop_index(op.f("ix_llm_usage_date"), table_name="llm_usage")
    op.drop_table("llm_usage")

    op.drop_index(op.f("ix_training_example_card_id"), table_name="training_example")
    op.drop_table("training_example")

    op.drop_index(op.f("ix_variation_cache_card_id"), table_name="variation_cache")
    op.drop_table("variation_cache")

    op.drop_index(op.f("ix_review_log_user_id"), table_name="review_log")
    op.drop_index(op.f("ix_review_log_card_id"), table_name="review_log")
    op.drop_table("review_log")

    op.drop_index(op.f("ix_card_deck_id"), table_name="card")
    op.drop_index(op.f("ix_card_card_type_id"), table_name="card")
    op.drop_table("card")

    op.drop_index(op.f("ix_deck_user_id"), table_name="deck")
    op.drop_table("deck")

    op.drop_index(op.f("ix_card_type_user_id"), table_name="card_type")
    op.drop_table("card_type")

    op.drop_index(op.f("ix_user_email"), table_name="user")
    op.drop_table("user")
