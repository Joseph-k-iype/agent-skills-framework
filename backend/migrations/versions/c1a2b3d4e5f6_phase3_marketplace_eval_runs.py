"""phase3: rework marketplace_listings + add eval_runs

Revision ID: c1a2b3d4e5f6
Revises: ba15738ac1a2
Create Date: 2026-06-29 20:30:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "c1a2b3d4e5f6"
down_revision: str | None = "ba15738ac1a2"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Rework marketplace_listings to key on the source concept + version.
    op.drop_index(op.f("ix_marketplace_listings_skill_node_id"), table_name="marketplace_listings")
    op.drop_table("marketplace_listings")
    op.create_table(
        "marketplace_listings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("source_workspace_id", sa.String(), nullable=False),
        sa.Column("source_path", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("type", sa.String(), nullable=True),
        sa.Column("runtime", sa.String(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("downloads", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "source_workspace_id", "source_path", "version", name="uq_listing_concept_version"
        ),
    )
    op.create_index(
        op.f("ix_marketplace_listings_source_workspace_id"),
        "marketplace_listings",
        ["source_workspace_id"],
        unique=False,
    )

    op.create_table(
        "eval_runs",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("workspace_id", sa.String(), nullable=False),
        sa.Column("concept_path", sa.String(), nullable=False),
        sa.Column("kind", sa.String(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("passed", sa.Boolean(), nullable=True),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("actor_id", sa.UUID(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_eval_runs_workspace_id"), "eval_runs", ["workspace_id"], unique=False)
    op.create_index(op.f("ix_eval_runs_concept_path"), "eval_runs", ["concept_path"], unique=False)
    op.create_index(op.f("ix_eval_runs_kind"), "eval_runs", ["kind"], unique=False)


def downgrade() -> None:
    op.drop_table("eval_runs")
    op.drop_index(
        op.f("ix_marketplace_listings_source_workspace_id"), table_name="marketplace_listings"
    )
    op.drop_table("marketplace_listings")
    op.create_table(
        "marketplace_listings",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("skill_node_id", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("summary", sa.String(), nullable=True),
        sa.Column("author_id", sa.UUID(), nullable=False),
        sa.Column("org_id", sa.UUID(), nullable=True),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("is_public", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("rating_avg", sa.Float(), nullable=False),
        sa.Column("downloads", sa.Integer(), nullable=False),
        sa.Column("tags", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False
        ),
        sa.ForeignKeyConstraint(["author_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["org_id"], ["organizations.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_marketplace_listings_skill_node_id"),
        "marketplace_listings",
        ["skill_node_id"],
        unique=False,
    )
