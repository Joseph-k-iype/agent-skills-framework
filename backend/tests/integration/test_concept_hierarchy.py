"""Integration tests for sub-concept PARENT_OF hierarchy with cycle prevention.

Task 5: wires the PARENT_OF graph edge from parent -> child, with cycle detection
so that self-parent and descendant-as-parent are both rejected.

Fixtures reuse the graph_name + setup pattern from test_concept_service.py.
"""

from __future__ import annotations

import uuid

import pytest

from app.api.deps import CurrentUser
from app.api.errors import CycleError
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.services.concept_service import ConceptService

pytestmark = pytest.mark.asyncio

WS = "ws_hier_" + uuid.uuid4().hex[:8]


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def setup(monkeypatch, tmp_path, graph_name):
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


async def _create(svc: ConceptService, ws: str, name: str, parent_path: str | None = None):
    return await svc.create(
        workspace_id=ws,
        folder_path="",
        name=name,
        type="skill",
        description=None,
        runtime=None,
        tags=[],
        capabilities=[],
        body="x",
        frontmatter={},
        parent_path=parent_path,
    )


async def test_set_parent_and_neighborhood(setup, admin_id):
    ws = "ws_hier_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))

        parent = await _create(svc, ws, "OCR")
        child = await _create(svc, ws, "Invoice OCR", parent_path=parent.path)

        # child neighborhood should report its parent
        nbr = svc.neighborhood(ws, child.path)
        assert nbr is not None
        assert nbr["parent"] == parent.path

        # parent neighborhood should list child among its children
        nbrp = svc.neighborhood(ws, parent.path)
        assert nbrp is not None
        assert child.path in nbrp["children"]


async def test_self_parent_rejected(setup, admin_id):
    ws = "ws_hier_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))

        a = await _create(svc, ws, "A")

        with pytest.raises(CycleError):
            await svc.update(workspace_id=ws, path=a.path, parent_path=a.path)


async def test_descendant_as_parent_rejected(setup, admin_id):
    ws = "ws_hier_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))

        a = await _create(svc, ws, "A")
        b = await _create(svc, ws, "B", parent_path=a.path)

        # making a's parent = b would create a->b->a cycle
        with pytest.raises(CycleError):
            await svc.update(workspace_id=ws, path=a.path, parent_path=b.path)


async def test_reparenting_leaves_single_edge(setup, admin_id):
    """After reparenting, there must be exactly one incoming PARENT_OF edge."""
    ws = "ws_hier_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))

        p1 = await _create(svc, ws, "P1")
        p2 = await _create(svc, ws, "P2")
        child = await _create(svc, ws, "Child", parent_path=p1.path)

        # Reparent child from p1 -> p2
        await svc.update(workspace_id=ws, path=child.path, parent_path=p2.path)

        nbr = svc.neighborhood(ws, child.path)
        assert nbr is not None
        assert nbr["parent"] == p2.path

        # p1 should no longer list child as a child
        nbr_p1 = svc.neighborhood(ws, p1.path)
        assert child.path not in (nbr_p1 or {}).get("children", [])


async def test_clear_parent(setup, admin_id):
    """Clearing parent removes the PARENT_OF edge."""
    ws = "ws_hier_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))

        parent = await _create(svc, ws, "Root")
        child = await _create(svc, ws, "Leaf", parent_path=parent.path)

        # Verify edge exists
        nbr = svc.neighborhood(ws, child.path)
        assert nbr["parent"] == parent.path

        # Explicitly clear parent
        await svc.update(workspace_id=ws, path=child.path, clear_parent=True)

        nbr2 = svc.neighborhood(ws, child.path)
        assert nbr2["parent"] is None
