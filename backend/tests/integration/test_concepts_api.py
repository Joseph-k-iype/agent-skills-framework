"""Concept file endpoints + search, through the real app."""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import CurrentUser, get_current_user
from app.auth.rbac import RoleName, permissions_for
from app.graph import client
from app.main import app

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_id() -> str:
    from app.db.session import SessionLocal
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def http(monkeypatch, tmp_path, graph_name):
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    # ASGITransport doesn't run lifespan, so bootstrap indexes on the test graph.
    from app.graph.indexes import bootstrap_indexes

    bootstrap_indexes()
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


def _login(role: str, user_id: str) -> None:
    app.dependency_overrides[get_current_user] = lambda: CurrentUser(
        id=user_id, role=role, permissions=permissions_for(role)
    )


async def test_concept_crud_and_search(http, admin_id):
    _login(RoleName.DEVELOPER, admin_id)
    async with http as c:
        ws = await c.post("/api/v1/workspaces", json={"name": "Finance " + uuid.uuid4().hex[:6]})
        ws_id = ws.json()["data"]["id"]

        created = await c.post(
            f"/api/v1/workspaces/{ws_id}/concepts",
            json={
                "name": "Invoice OCR",
                "folder_path": "payments",
                "type": "skill",
                "runtime": "python 3.12",
                "body": "# OCR\nExtracts invoice line items.",
            },
        )
        assert created.status_code == 200, created.text
        path = created.json()["data"]["path"]
        assert path == "payments/invoice-ocr.md"
        assert created.json()["data"]["runtime"] == "python 3.12"

        got = await c.get(
            f"/api/v1/workspaces/{ws_id}/concept", params={"path": path}
        )
        assert got.status_code == 200
        assert "Extracts invoice" in got.json()["data"]["body"]

        listed = await c.get(f"/api/v1/workspaces/{ws_id}/concepts")
        assert any(x["path"] == path for x in listed.json()["data"])

        found = await c.get(
            f"/api/v1/workspaces/{ws_id}/search", params={"q": "invoice extraction"}
        )
        assert found.status_code == 200
        assert any(r["path"] == path for r in found.json()["data"])


async def test_consumer_cannot_create_concept(http, admin_id):
    _login(RoleName.DEVELOPER, admin_id)
    async with http as c:
        ws = await c.post("/api/v1/workspaces", json={"name": "X " + uuid.uuid4().hex[:6]})
        ws_id = ws.json()["data"]["id"]

    _login(RoleName.CONSUMER, str(uuid.uuid4()))
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        res = await c.post(
            f"/api/v1/workspaces/{ws_id}/concepts",
            json={"name": "Nope", "type": "skill"},
        )
        assert res.status_code == 403
