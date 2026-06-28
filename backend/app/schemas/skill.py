from __future__ import annotations

from pydantic import BaseModel, Field


class SkillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    folder_id: str
    workspace_id: str | None = None
    description: str | None = None
    runtime: str = "python"
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)


class SkillUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    runtime: str | None = None
    tags: list[str] | None = None
    capabilities: list[str] | None = None
    references: list[str] | None = None  # OKF document ids


class SkillPublish(BaseModel):
    version: str | None = None  # if set and newer, creates a new version node


class SkillClone(BaseModel):
    folder_id: str
    name: str | None = None


class SkillRef(BaseModel):
    id: str
    title: str | None = None


class SkillOut(BaseModel):
    id: str
    skill_key: str
    name: str
    description: str | None = None
    runtime: str = "python"
    version: str = "0.1.0"
    status: str = "draft"
    is_current: bool = True
    workspace_id: str | None = None
    folder_id: str | None = None
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    references: list[SkillRef] = Field(default_factory=list)
    created_at: str | None = None
    updated_at: str | None = None


class SkillVersions(BaseModel):
    skill_key: str
    versions: list[SkillOut]
