from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class MarketplaceListing(Base, TimestampMixin):
    """Marketplace metadata for a published skill. The skill itself is a
    FalkorDB node; this row holds the relational/commercial metadata."""

    __tablename__ = "marketplace_listings"

    id: Mapped[uuid.UUID] = uuid_pk()
    skill_node_id: Mapped[str] = mapped_column(index=True)  # FalkorDB Skill node id
    title: Mapped[str]
    summary: Mapped[str | None] = mapped_column(default=None)
    author_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("users.id"))
    org_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), default=None
    )
    version: Mapped[str]
    is_public: Mapped[bool] = mapped_column(default=False)
    status: Mapped[str] = mapped_column(default="draft")  # draft|pending|published
    rating_avg: Mapped[float] = mapped_column(default=0.0)
    downloads: Mapped[int] = mapped_column(default=0)
    tags: Mapped[list] = mapped_column(JSONB, default=list)
