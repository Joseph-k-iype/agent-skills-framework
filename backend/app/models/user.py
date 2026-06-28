from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import ForeignKey
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, uuid_pk

if TYPE_CHECKING:
    from app.models.role import Role


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = uuid_pk()
    username: Mapped[str] = mapped_column(unique=True, index=True)
    email: Mapped[str | None] = mapped_column(unique=True, default=None)
    full_name: Mapped[str | None] = mapped_column(default=None)

    # Dev-admin fallback: hashed_password is set only for local admin login.
    is_dev_admin: Mapped[bool] = mapped_column(default=False)
    hashed_password: Mapped[str | None] = mapped_column(default=None)
    # LDAP users carry their distinguished name; null for the dev admin.
    ldap_dn: Mapped[str | None] = mapped_column(default=None)

    org_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("organizations.id"), default=None
    )
    role_id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), ForeignKey("roles.id"))
    role: Mapped[Role] = relationship(lazy="selectin")

    is_active: Mapped[bool] = mapped_column(default=True)
