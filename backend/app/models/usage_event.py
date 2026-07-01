from __future__ import annotations

import uuid

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class UsageEvent(Base, TimestampMixin):
    """An SDK consumption event for a marketplace listing.

    ``kind`` is ``fetch`` (skill content pulled) or ``apply`` (skill used in an
    LLM call and reported back). Feeds the insight dashboards' "most used".
    """

    __tablename__ = "usage_events"

    id: Mapped[uuid.UUID] = uuid_pk()
    listing_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("marketplace_listings.id"), index=True
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(PG_UUID(as_uuid=True), default=None)
    api_key_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("api_keys.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        default=None,
    )
    kind: Mapped[str] = mapped_column(index=True)
    meta: Mapped[dict] = mapped_column(JSONB, default=dict)
