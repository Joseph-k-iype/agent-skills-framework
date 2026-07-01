from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class MarketplaceListing(Base, TimestampMixin):
    """Marketplace metadata for a published concept version.

    The concept itself stays in its git-backed workspace bundle (the source of
    truth); this row is the relational catalog entry so a listing can be
    discovered and installed (copied) into another workspace. Keyed by the source
    concept + version.
    """

    __tablename__ = "marketplace_listings"
    __table_args__ = (
        UniqueConstraint(
            "source_workspace_id", "source_path", name="uq_listing_concept"
        ),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    source_workspace_id: Mapped[str] = mapped_column(index=True)
    source_path: Mapped[str] = mapped_column()
    title: Mapped[str]
    summary: Mapped[str | None] = mapped_column(default=None)
    type: Mapped[str | None] = mapped_column(default=None)
    runtime: Mapped[str | None] = mapped_column(default=None)
    author_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), default=None
    )
    version: Mapped[str]
    tags: Mapped[list] = mapped_column(JSONB, default=list)
    capabilities: Mapped[list] = mapped_column(JSONB, default=list)
    sources: Mapped[list] = mapped_column(JSONB, default=list)
    is_public: Mapped[bool] = mapped_column(default=True)
    downloads: Mapped[int] = mapped_column(default=0)
    clones: Mapped[int] = mapped_column(default=0)
    category: Mapped[str | None] = mapped_column(default=None, index=True)
    featured: Mapped[bool] = mapped_column(default=False, index=True)
    latest_sha: Mapped[str | None] = mapped_column(default=None)
    latest_version: Mapped[int | None] = mapped_column(default=None)
