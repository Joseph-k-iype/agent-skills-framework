"""In-process API tests through the real app (httpx ASGI), real PG + FalkorDB.

Auth is exercised by overriding ``get_current_user`` with role-scoped users so we
can assert RBAC (403s) and the success envelope without minting JWTs per test.
"""

from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.deps import CurrentUser, get_current_user
from app.auth.rbac import RoleName, permissions_for
from app.main import app


def _user(role: str, user_id: str) -> CurrentUser:
    return CurrentUser(id=user_id, role=role, permissions=permissions_for(role))


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
async def admin_id() -> str:
    """The seeded dev-admin's id — used as a real actor for audit FK integrity."""
    from app.db.session import SessionLocal
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


def _login_as(role: str, user_id: str | None = None) -> None:
    app.dependency_overrides[get_current_user] = lambda: _user(role, user_id or str(uuid.uuid4()))


@pytest.fixture(autouse=True)
def _cleanup_overrides():
    yield
    app.dependency_overrides.pop(get_current_user, None)


async def test_health_envelope(client):
    res = await client.get("/api/v1/healthz")
    assert res.status_code == 200
    body = res.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"


async def test_consumer_cannot_create_workspace(client):
    _login_as(RoleName.CONSUMER)
    res = await client.post("/api/v1/workspaces", json={"name": "Nope"})
    assert res.status_code == 403
    body = res.json()
    assert body["success"] is False
    assert body["error"]["code"] == "FORBIDDEN"


async def test_developer_workspace_lifecycle(client, graph_name, admin_id):
    _login_as(RoleName.DEVELOPER, admin_id)

    created = await client.post("/api/v1/workspaces", json={"name": "Ops"})
    assert created.status_code == 200
    ws_id = created.json()["data"]["id"]

    folder = await client.post(
        "/api/v1/folders",
        json={"name": "Runbooks", "workspace_id": ws_id, "parent_id": ws_id},
    )
    assert folder.status_code == 200
    assert folder.json()["data"]["path"] == "/runbooks"

    tree = await client.get(f"/api/v1/workspaces/{ws_id}")
    assert tree.status_code == 200
    assert len(tree.json()["data"]["folders"]) == 1

    deleted = await client.delete(f"/api/v1/workspaces/{ws_id}")
    assert deleted.status_code == 200


async def test_unauthenticated_is_rejected(client):
    # no override -> real get_current_user runs and finds no bearer token
    res = await client.get("/api/v1/workspaces")
    assert res.status_code == 401
