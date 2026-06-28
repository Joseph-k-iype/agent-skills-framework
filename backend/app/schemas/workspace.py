from __future__ import annotations

from pydantic import BaseModel, Field


class WorkspaceCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    description: str | None = None


class WorkspaceUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None


class WorkspaceOut(BaseModel):
    id: str
    name: str
    description: str | None = None
    owner: str | None = None
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None


class FolderCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    workspace_id: str
    # parent may be the workspace id (top-level) or another folder id
    parent_id: str


class FolderUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=120)


class FolderMove(BaseModel):
    new_parent_id: str


class FolderOut(BaseModel):
    id: str
    name: str
    path: str | None = None
    workspace_id: str
    parent_id: str | None = None
    status: str = "active"
    created_at: str | None = None
    updated_at: str | None = None


class WorkspaceTree(BaseModel):
    workspace: WorkspaceOut
    folders: list[FolderOut]
