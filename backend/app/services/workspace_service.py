"""Workspace + Folder business logic: hierarchy, paths, cycle guard, audit."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.errors import ConflictError, NotFoundError, ValidationError
from app.events.types import EventType
from app.repositories.workspace_graph_repo import WorkspaceGraphRepository
from app.schemas.workspace import (
    FolderCreate,
    FolderMove,
    FolderOut,
    FolderUpdate,
    WorkspaceCreate,
    WorkspaceOut,
    WorkspaceTree,
    WorkspaceUpdate,
)
from app.services.audit_service import AuditService
from app.services.index_service import IndexService
from app.storage.repo import BundleRepo


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _slug(name: str) -> str:
    return name.strip().lower().replace(" ", "-")


def _rel(path: str) -> str:
    """Graph paths are stored with a leading '/'; bundle paths are relative."""
    return path.lstrip("/")


class WorkspaceService:
    def __init__(self, db: AsyncSession, user: CurrentUser):
        self.db = db
        self.user = user
        self.repo = WorkspaceGraphRepository()
        self.audit = AuditService(db)
        self.index = IndexService()

    # ── workspaces ──
    async def create_workspace(self, body: WorkspaceCreate) -> WorkspaceOut:
        node = self.repo.create_workspace(
            id=_new_id(),
            name=body.name,
            description=body.description,
            owner=self.user.id,
            ts=_now(),
        )
        # The workspace IS a git-backed OKF bundle on disk.
        BundleRepo.init(node["id"])
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.WORKSPACE_CREATED,
            resource_type="Workspace",
            resource_id=node["id"],
            workspace_id=node["id"],
            payload={"name": node["name"]},
        )
        return WorkspaceOut(**node)

    def list_workspaces(self) -> list[WorkspaceOut]:
        nodes = self.repo.list_workspaces(owner=self.user.id, is_admin=self.user.role == "admin")
        return [WorkspaceOut(**n) for n in nodes]

    def _require_workspace(self, workspace_id: str) -> dict:
        ws = self.repo.get_workspace(workspace_id)
        if ws is None:
            raise NotFoundError("Workspace not found")
        return ws

    def get_tree(self, workspace_id: str) -> WorkspaceTree:
        ws = self._require_workspace(workspace_id)
        folders = self.repo.get_subtree(workspace_id)
        return WorkspaceTree(
            workspace=WorkspaceOut(**ws),
            folders=[FolderOut(**f) for f in folders],
        )

    async def update_workspace(self, workspace_id: str, body: WorkspaceUpdate) -> WorkspaceOut:
        self._require_workspace(workspace_id)
        node = self.repo.update_workspace(
            id=workspace_id, name=body.name, description=body.description, ts=_now()
        )
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.WORKSPACE_UPDATED,
            resource_type="Workspace",
            resource_id=workspace_id,
            workspace_id=workspace_id,
        )
        return WorkspaceOut(**node)  # type: ignore[arg-type]

    async def delete_workspace(self, workspace_id: str) -> None:
        self._require_workspace(workspace_id)
        self.repo.delete_workspace(workspace_id)
        self.index.repo.clear_workspace(workspace_id)
        # Remove the on-disk bundle.
        bundle = BundleRepo(workspace_id)
        if bundle.exists:
            import shutil

            shutil.rmtree(bundle.root, ignore_errors=True)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.WORKSPACE_DELETED,
            resource_type="Workspace",
            resource_id=workspace_id,
            workspace_id=workspace_id,
        )

    # ── folders ──
    def _container_path(self, container_id: str, workspace_id: str) -> str:
        """Path prefix of a container (workspace root => '', folder => its path)."""
        if container_id == workspace_id:
            return ""
        parent = self.repo.get_folder(container_id)
        if parent is None:
            raise NotFoundError("Parent folder not found")
        if parent.get("workspace_id") != workspace_id:
            raise ValidationError("Parent folder belongs to a different workspace")
        return parent.get("path") or ""

    async def create_folder(self, body: FolderCreate) -> FolderOut:
        self._require_workspace(body.workspace_id)
        prefix = self._container_path(body.parent_id, body.workspace_id)
        path = f"{prefix}/{_slug(body.name)}"
        node = self.repo.create_folder(
            id=_new_id(),
            name=body.name,
            path=path,
            workspace_id=body.workspace_id,
            parent_id=body.parent_id,
            ts=_now(),
        )
        if node is None:
            raise NotFoundError("Parent container not found")
        node["parent_id"] = body.parent_id
        # Create the real directory in the bundle (persisted via .gitkeep).
        BundleRepo.init(body.workspace_id).add_dir(
            _rel(path), f"create folder {path}", self.user.id
        )
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.FOLDER_CREATED,
            resource_type="Folder",
            resource_id=node["id"],
            workspace_id=body.workspace_id,
            payload={"name": body.name, "path": path},
        )
        return FolderOut(**node)

    def _require_folder(self, folder_id: str) -> dict:
        f = self.repo.get_folder(folder_id)
        if f is None:
            raise NotFoundError("Folder not found")
        return f

    def get_folder(self, folder_id: str) -> FolderOut:
        f = self._require_folder(folder_id)
        parent = self.repo.get_parent(folder_id)
        f["parent_id"] = parent["id"] if parent else None
        return FolderOut(**f)

    def _recompute_subtree_paths(self, folder_id: str, new_path: str) -> None:
        """Rewrite ``path`` for a folder and every descendant under it."""
        root, descendants = self.repo.get_folder_subtree(folder_id)
        if root is None:
            return
        old_prefix = root.get("path") or ""
        ts = _now()
        self.repo.set_folder_path(id=folder_id, path=new_path, ts=ts)
        for d in descendants:
            d_path = d.get("path") or ""
            suffix = (
                d_path[len(old_prefix) :] if d_path.startswith(old_prefix) else f"/{d.get('name')}"
            )
            self.repo.set_folder_path(id=d["id"], path=f"{new_path}{suffix}", ts=ts)

    async def rename_folder(self, folder_id: str, body: FolderUpdate) -> FolderOut:
        folder = self._require_folder(folder_id)
        old_path = folder.get("path") or ""
        workspace_id = folder.get("workspace_id")
        parent = self.repo.get_parent(folder_id)
        prefix = ""
        if parent and parent.get("type") == "Folder":
            prefix = parent.get("path") or ""
        new_path = f"{prefix}/{_slug(body.name)}"
        node = self.repo.rename_folder(id=folder_id, name=body.name, ts=_now())
        self._recompute_subtree_paths(folder_id, new_path)
        await self._move_dir_and_reindex(workspace_id, old_path, new_path)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.FOLDER_UPDATED,
            resource_type="Folder",
            resource_id=folder_id,
            workspace_id=node.get("workspace_id") if node else None,
            payload={"name": body.name},
        )
        out = self.repo.get_folder(folder_id) or node or {}
        out["parent_id"] = parent["id"] if parent else None
        return FolderOut(**out)

    async def move_folder(self, folder_id: str, body: FolderMove) -> FolderOut:
        folder = self._require_folder(folder_id)
        old_path = folder.get("path") or ""
        target = body.new_parent_id
        workspace_id = folder.get("workspace_id")

        # Target must exist and live in the same workspace.
        if target != workspace_id:
            target_folder = self.repo.get_folder(target)
            if target_folder is None:
                raise NotFoundError("Target parent not found")
            if target_folder.get("workspace_id") != workspace_id:
                raise ValidationError("Cannot move a folder across workspaces")

        # Cycle guard: cannot move into self or a descendant.
        if self.repo.is_descendant(id=folder_id, target_id=target):
            raise ConflictError("Cannot move a folder into itself or one of its descendants")

        self.repo.move_folder(id=folder_id, new_parent_id=target, ts=_now())
        prefix = self._container_path(target, workspace_id) if workspace_id else ""
        new_path = f"{prefix}/{_slug(folder.get('name', ''))}"
        self._recompute_subtree_paths(folder_id, new_path)
        await self._move_dir_and_reindex(workspace_id, old_path, new_path)

        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.FOLDER_MOVED,
            resource_type="Folder",
            resource_id=folder_id,
            workspace_id=workspace_id,
            payload={"new_parent_id": target},
        )
        out = self.repo.get_folder(folder_id) or {}
        out["parent_id"] = target
        return FolderOut(**out)

    async def delete_folder(self, folder_id: str) -> None:
        folder = self._require_folder(folder_id)
        path = folder.get("path") or ""
        workspace_id = folder.get("workspace_id")
        self.repo.delete_folder(folder_id)
        if workspace_id:
            bundle = BundleRepo(workspace_id)
            if bundle.exists and bundle.dir_exists(_rel(path)):
                bundle.delete_dir(_rel(path), f"delete folder {path}", self.user.id)
                await self.index.reindex_workspace(workspace_id)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.FOLDER_DELETED,
            resource_type="Folder",
            resource_id=folder_id,
            workspace_id=folder.get("workspace_id"),
        )

    async def _move_dir_and_reindex(
        self, workspace_id: str | None, old_path: str, new_path: str
    ) -> None:
        """Move a folder's on-disk directory and refresh the graph projection.

        Concept node keys are path-based, so a structural folder change requires
        a reindex to keep the projection consistent with the files.
        """
        if not workspace_id or old_path == new_path:
            return
        bundle = BundleRepo(workspace_id)
        if not bundle.exists:
            return
        src, dst = _rel(old_path), _rel(new_path)
        if bundle.dir_exists(src) and not bundle.dir_exists(dst):
            bundle.move_dir(src, dst, f"move folder {old_path} -> {new_path}", self.user.id)
            await self.index.reindex_workspace(workspace_id)
