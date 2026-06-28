"""Pure unit tests for password hashing + JWT (no DB / network)."""

from __future__ import annotations

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)


def test_password_hash_roundtrip():
    h = hash_password("s3cret")
    assert h != "s3cret"
    assert verify_password("s3cret", h)
    assert not verify_password("wrong", h)


def test_password_over_72_bytes_does_not_crash():
    long = "x" * 200
    h = hash_password(long)
    assert verify_password(long, h)


def test_access_token_carries_role_and_perms():
    tok = create_access_token("user-1", "admin", ["skill:create"])
    payload = decode_token(tok)
    assert payload["sub"] == "user-1"
    assert payload["role"] == "admin"
    assert payload["perms"] == ["skill:create"]
    assert payload["type"] == "access"


def test_refresh_token_typed_and_decodable():
    tok, exp = create_refresh_token("user-1")
    payload = decode_token(tok)
    assert payload["type"] == "refresh"
    assert exp is not None


def test_decode_rejects_garbage():
    with pytest.raises(ValueError):
        decode_token("not-a-jwt")
