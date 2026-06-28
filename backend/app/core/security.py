"""JWT issuance/verification and password hashing."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

_pwd = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw: str) -> str:
    return _pwd.hash(raw)


def verify_password(raw: str, hashed: str) -> bool:
    return _pwd.verify(raw, hashed)


def hash_token(token: str) -> str:
    """Stable hash for storing refresh tokens at rest."""
    return hashlib.sha256(token.encode()).hexdigest()


def _now() -> datetime:
    return datetime.now(timezone.utc)


def create_access_token(sub: str, role: str, perms: list[str]) -> str:
    payload: dict[str, Any] = {
        "sub": sub,
        "role": role,
        "perms": perms,
        "type": "access",
        "iat": _now(),
        "exp": _now() + timedelta(minutes=settings.jwt_access_ttl_min),
        "jti": uuid.uuid4().hex,
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def create_refresh_token(sub: str) -> tuple[str, datetime]:
    exp = _now() + timedelta(days=settings.jwt_refresh_ttl_days)
    payload = {"sub": sub, "type": "refresh", "iat": _now(), "exp": exp, "jti": uuid.uuid4().hex}
    token = jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)
    return token, exp


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:  # pragma: no cover - thin wrapper
        raise ValueError("invalid token") from exc
