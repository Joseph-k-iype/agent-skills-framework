"""listing_clones

Revision ID: a5e6f7a8b9c0
Revises: a1b2c3d4e5f6
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op

revision = "a5e6f7a8b9c0"
down_revision = "a1b2c3d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "marketplace_listings",
        sa.Column("clones", sa.Integer(), nullable=False, server_default="0"),
    )


def downgrade() -> None:
    op.drop_column("marketplace_listings", "clones")
