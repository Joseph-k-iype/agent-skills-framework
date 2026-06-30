"""Public marketplace endpoints — unauthenticated, in-process ASGI tests.

These hit the real app (httpx ASGI transport) against real PG + FalkorDB, with
NO Authorization header and no ``get_current_user`` override, to prove the
``/public/*`` routes take no auth dependency at all.
"""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def test_public_list_requires_no_auth(client):
    # No Authorization header at all.
    resp = await client.get("/api/v1/public/marketplace")
    assert resp.status_code == 200
    body = resp.json()
    assert body["success"] is True
    assert isinstance(body["data"], list)


async def test_public_categories_no_auth(client):
    resp = await client.get("/api/v1/public/marketplace/categories")
    assert resp.status_code == 200
    assert resp.json()["success"] is True
