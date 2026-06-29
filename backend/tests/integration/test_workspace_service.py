"""Workspaces are git repos; folders are real directories on disk."""

from __future__ import annotations

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.schemas.workspace import FolderCreate, FolderMove, FolderUpdate, WorkspaceCreate
from app.services.workspace_service import WorkspaceService
from app.storage import paths
from app.storage.repo import BundleRepo

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
    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


async def test_create_workspace_makes_git_repo(setup, admin_id):
    async with SessionLocal() as db:
        svc = WorkspaceService(db, _user(admin_id))
        ws = await svc.create_workspace(WorkspaceCreate(name="Finance"))
        assert BundleRepo(ws.id).exists


async def test_folder_create_move_delete_on_disk(setup, admin_id):
    async with SessionLocal() as db:
        svc = WorkspaceService(db, _user(admin_id))
        ws = await svc.create_workspace(WorkspaceCreate(name="Ops"))
        bundle = BundleRepo(ws.id)

        a = await svc.create_folder(
            FolderCreate(name="Payments", workspace_id=ws.id, parent_id=ws.id)
        )
        assert bundle.dir_exists("payments")

        b = await svc.create_folder(
            FolderCreate(name="Archive", workspace_id=ws.id, parent_id=ws.id)
        )
        assert bundle.dir_exists("archive")

        # move 'payments' under 'archive'
        await svc.move_folder(a.id, FolderMove(new_parent_id=b.id))
        assert bundle.dir_exists("archive/payments")
        assert not bundle.dir_exists("payments")

        # rename it
        await svc.rename_folder(a.id, FolderUpdate(name="Invoices"))
        assert bundle.dir_exists("archive/invoices")

        # delete archive (with its subtree)
        await svc.delete_folder(b.id)
        assert not bundle.dir_exists("archive")
