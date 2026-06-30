from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin, uuid_pk


class ApiKey(Base, TimestampMixin):
    """A long-lived API key for the SDK / programmatic access.

    Only a sha256 hash of the full key is stored; the plaintext ``sk_live_…`` is
    shown to the user exactly once at creation. ``prefix`` is a short, safe-to-show
    fragment for identifying the key in the UI.
    """

    __tablename__ = "api_keys"

    id: Mapped[uuid.UUID] = uuid_pk()
    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    name: Mapped[str]
    prefix: Mapped[str]
    key_hash: Mapped[str] = mapped_column(unique=True, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
