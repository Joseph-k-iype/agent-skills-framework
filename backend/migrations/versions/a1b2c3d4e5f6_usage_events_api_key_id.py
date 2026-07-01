"""usage_events_api_key_id

Revision ID: a1b2c3d4e5f6
Revises: f4d5e6f7a8b9
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "a1b2c3d4e5f6"
down_revision = "f4d5e6f7a8b9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "usage_events",
        sa.Column(
            "api_key_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("api_keys.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index(
        "ix_usage_events_api_key_id",
        "usage_events",
        ["api_key_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_usage_events_api_key_id", table_name="usage_events")
    op.drop_column("usage_events", "api_key_id")
