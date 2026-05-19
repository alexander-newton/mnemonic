"""Seed builtin card types

Revision ID: 0002
Revises: 0001
Create Date: 2025-02-03 14:00:01.000000

This migration creates the four builtin card types:
- Basic (front/back)
- BasicReversed (front/back with automatic reverse)
- Cloze (cloze deletion)
- ImageCloze (image cloze with regions)
"""
import json
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert builtin card types."""
    # Define the builtin card types with JSON data
    card_types = [
        {
            "id": "00000000-0000-0000-0000-000000000001",
            "name": "Basic",
            "description": "Front/back flashcard with a question on the front and answer on the back",
            "syntax_type": "frontback",
            "fields": json.dumps([{"name": "front", "label": "Front"}, {"name": "back", "label": "Back"}]),
            "render_pipeline": json.dumps(["pandoc", "mathjax"]),
        },
        {
            "id": "00000000-0000-0000-0000-000000000002",
            "name": "BasicReversed",
            "description": "Front/back flashcard that automatically generates a reverse card",
            "syntax_type": "frontback",
            "fields": json.dumps([{"name": "front", "label": "Front"}, {"name": "back", "label": "Back"}]),
            "render_pipeline": json.dumps(["pandoc", "mathjax"]),
        },
        {
            "id": "00000000-0000-0000-0000-000000000003",
            "name": "Cloze",
            "description": "Cloze deletion card with {{cloze:n::answer}} syntax",
            "syntax_type": "cloze",
            "fields": json.dumps([{"name": "text", "label": "Text"}]),
            "render_pipeline": json.dumps(["pandoc", "mathjax"]),
        },
        {
            "id": "00000000-0000-0000-0000-000000000004",
            "name": "ImageCloze",
            "description": "Image cloze with {{region:n::x,y,w,h::label}} syntax for highlighting regions",
            "syntax_type": "image_cloze",
            "fields": json.dumps([{"name": "image", "label": "Image"}, {"name": "regions", "label": "Regions"}]),
            "render_pipeline": json.dumps(["pandoc", "mathjax"]),
        },
    ]

    # Use bulk_insert for efficiency
    # Use datetime.now() instead of sa.func.now() for compatibility with SQLite and PostgreSQL
    now = datetime.utcnow()
    op.bulk_insert(
        sa.table(
            "card_type",
            sa.column("id"),
            sa.column("user_id"),
            sa.column("name"),
            sa.column("description"),
            sa.column("parent_type_id"),
            sa.column("syntax_type"),
            sa.column("fields"),
            sa.column("render_pipeline"),
            sa.column("is_builtin"),
            sa.column("created_at"),
            sa.column("updated_at"),
        ),
        [
            {
                "id": ct["id"],
                "user_id": None,
                "name": ct["name"],
                "description": ct["description"],
                "parent_type_id": None,
                "syntax_type": ct["syntax_type"],
                "fields": ct["fields"],
                "render_pipeline": ct["render_pipeline"],
                "is_builtin": True,
                "created_at": now,
                "updated_at": now,
            }
            for ct in card_types
        ],
    )


def downgrade() -> None:
    """Remove all builtin card types."""
    op.execute(
        sa.text(
            "DELETE FROM card_type WHERE is_builtin = TRUE AND user_id IS NULL"
        )
    )
