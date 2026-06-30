"""skill_versions and listing meta

Revision ID: e3c4d5f6a7b8
Revises: d2b3c4e5f6a7
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

revision = "e3c4d5f6a7b8"
down_revision = "d2b3c4e5f6a7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("marketplace_listings", sa.Column("category", sa.String(), nullable=True))
    op.add_column(
        "marketplace_listings",
        sa.Column("featured", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column("marketplace_listings", sa.Column("latest_sha", sa.String(), nullable=True))
    op.add_column("marketplace_listings", sa.Column("latest_version", sa.Integer(), nullable=True))
    op.create_index("ix_marketplace_listings_category", "marketplace_listings", ["category"])
    op.create_index("ix_marketplace_listings_featured", "marketplace_listings", ["featured"])

    op.create_table(
        "skill_versions",
        sa.Column("id", PG_UUID(as_uuid=True), primary_key=True),
        sa.Column("listing_id", PG_UUID(as_uuid=True), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("content_sha", sa.String(), nullable=False),
        sa.Column("changelog", sa.String(), nullable=True),
        sa.Column("content", sa.String(), nullable=False),
        sa.Column("downloads", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(["listing_id"], ["marketplace_listings.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("listing_id", "version", name="uq_skillversion_listing_version"),
        sa.UniqueConstraint("listing_id", "content_sha", name="uq_skillversion_listing_sha"),
    )
    op.create_index("ix_skill_versions_listing_id", "skill_versions", ["listing_id"])
    op.create_index("ix_skill_versions_content_sha", "skill_versions", ["content_sha"])

    # Backfill: one version per existing listing. SHA derived from id+version so it
    # is stable and unique without needing to re-read bundle content here.
    op.execute(
        """
        INSERT INTO skill_versions (id, listing_id, version, content_sha, content, downloads, created_at, updated_at)
        SELECT gen_random_uuid(), id, 1,
               encode(sha256((id::text || ':' || coalesce(version,'1'))::bytea), 'hex'),
               '', coalesce(downloads,0), now(), now()
        FROM marketplace_listings
        """
    )
    op.execute(
        "UPDATE marketplace_listings ml SET latest_version = 1, "
        "latest_sha = (SELECT content_sha FROM skill_versions sv WHERE sv.listing_id = ml.id LIMIT 1)"
    )

    # De-duplicate listings to one row per (workspace, path) before the unique swap,
    # keeping the most recently created. Versions of removed dups cascade-delete.
    op.execute(
        """
        DELETE FROM marketplace_listings a
        USING marketplace_listings b
        WHERE a.source_workspace_id = b.source_workspace_id
          AND a.source_path = b.source_path
          AND (a.created_at < b.created_at
               OR (a.created_at = b.created_at AND a.ctid < b.ctid))
        """
    )

    # Swap the unique constraint from (workspace, path, version) to (workspace, path).
    op.drop_constraint("uq_listing_concept_version", "marketplace_listings", type_="unique")
    op.create_unique_constraint(
        "uq_listing_concept", "marketplace_listings", ["source_workspace_id", "source_path"]
    )


def downgrade() -> None:
    op.drop_constraint("uq_listing_concept", "marketplace_listings", type_="unique")
    op.create_unique_constraint(
        "uq_listing_concept_version",
        "marketplace_listings",
        ["source_workspace_id", "source_path", "version"],
    )
    op.drop_index("ix_skill_versions_content_sha", "skill_versions")
    op.drop_index("ix_skill_versions_listing_id", "skill_versions")
    op.drop_table("skill_versions")
    op.drop_index("ix_marketplace_listings_featured", "marketplace_listings")
    op.drop_index("ix_marketplace_listings_category", "marketplace_listings")
    op.drop_column("marketplace_listings", "latest_version")
    op.drop_column("marketplace_listings", "latest_sha")
    op.drop_column("marketplace_listings", "featured")
    op.drop_column("marketplace_listings", "category")
