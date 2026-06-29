"""File-backed concept CRUD with git history + graph reindex."""

from __future__ import annotations

import uuid

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.services.concept_service import ConceptService

pytestmark = pytest.mark.asyncio


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


async def test_create_then_get(setup, admin_id):
    ws = "ws_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        out = await svc.create(
            workspace_id=ws,
            folder_path="finance/payments",
            name="Invoice OCR",
            type="skill",
            description="Extracts line items",
            runtime="python 3.12",
            tags=["finance"],
            capabilities=["extraction:invoice"],
            body="# OCR\n",
            frontmatter={"owner": "jo"},
        )
        assert out.path == "finance/payments/invoice-ocr.md"
        assert out.runtime == "python 3.12"
        assert out.frontmatter["owner"] == "jo"
        assert svc.get(ws, out.path).title == "Invoice OCR"


async def test_update_grows_history(setup, admin_id):
    ws = "ws_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        out = await svc.create(
            workspace_id=ws, folder_path="", name="Doc", type="doc",
            description=None, runtime=None, tags=[], capabilities=[], body="v1", frontmatter={},
        )
        await svc.update(workspace_id=ws, path=out.path, body="v2")
        assert len(svc.history(ws, out.path)) == 2
        assert svc.get(ws, out.path).body.strip() == "v2"


async def test_move_and_delete(setup, admin_id):
    ws = "ws_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        svc = ConceptService(db, _user(admin_id))
        out = await svc.create(
            workspace_id=ws, folder_path="a", name="X", type="skill",
            description=None, runtime=None, tags=[], capabilities=[], body="b", frontmatter={},
        )
        moved = await svc.move(workspace_id=ws, src_path=out.path, dst_folder_path="b")
        assert moved.path == "b/x.md"
        await svc.delete(workspace_id=ws, path=moved.path)
        assert svc.list_concepts(ws) == []
