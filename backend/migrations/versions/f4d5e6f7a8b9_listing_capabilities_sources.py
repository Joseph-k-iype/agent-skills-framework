"""listing_capabilities_sources

Revision ID: f4d5e6f7a8b9
Revises: e3c4d5f6a7b8
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB

revision = "f4d5e6f7a8b9"
down_revision = "e3c4d5f6a7b8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketplace_listings",
        sa.Column(
            "capabilities",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.add_column(
        "marketplace_listings",
        sa.Column(
            "sources",
            JSONB,
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )


def downgrade() -> None:
    op.drop_column("marketplace_listings", "sources")
    op.drop_column("marketplace_listings", "capabilities")
