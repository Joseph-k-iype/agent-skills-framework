from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class SkillVersion(Base, TimestampMixin):
    """An immutable, content-addressed snapshot of a published skill version."""

    __tablename__ = "skill_versions"
    __table_args__ = (
        UniqueConstraint("listing_id", "version", name="uq_skillversion_listing_version"),
        UniqueConstraint("listing_id", "content_sha", name="uq_skillversion_listing_sha"),
    )

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("marketplace_listings.id", ondelete="CASCADE"),
        index=True,
    )
    version: Mapped[int] = mapped_column()
    content_sha: Mapped[str] = mapped_column(index=True)
    changelog: Mapped[str | None] = mapped_column(default=None)
    content: Mapped[str] = mapped_column()
    downloads: Mapped[int] = mapped_column(default=0)
