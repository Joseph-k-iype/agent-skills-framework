"""API schemas for OKF concept files (skills/agents/prompts/docs)."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ConceptCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    folder_path: str = ""  # repo-relative dir; "" = bundle root
    type: str = "skill"  # free text — no enum
    description: str | None = None
    runtime: str | None = None  # free text
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    parent_path: str | None = None  # carried here; edge wired in Task 5
    body: str = ""
    frontmatter: dict = Field(default_factory=dict)  # extra/unknown keys preserved


class ConceptUpdate(BaseModel):
    title: str | None = None
    type: str | None = None
    description: str | None = None
    runtime: str | None = None
    tags: list[str] | None = None
    capabilities: list[str] | None = None
    sources: list[str] | None = None
    parent_path: str | None = None  # carried here; edge wired in Task 5
    body: str | None = None
    frontmatter: dict | None = None


class ConceptMove(BaseModel):
    dst_folder_path: str = ""


class ConceptPublish(BaseModel):
    version: str = Field(min_length=1)


class EvalCase(BaseModel):
    input: str = ""
    expected: str = ""


class EvalCasesBody(BaseModel):
    cases: list[EvalCase] = Field(default_factory=list)


class ConceptRef(BaseModel):
    path: str
    title: str | None = None
    type: str | None = None


class VersionEntry(BaseModel):
    sha: str
    message: str
    author: str
    ts: str


class ConceptOut(BaseModel):
    workspace_id: str
    path: str
    type: str
    title: str
    description: str | None = None
    runtime: str | None = None
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    parent_path: str | None = None  # carried here; edge wired in Task 5
    body: str = ""
    frontmatter: dict = Field(default_factory=dict)
    links: list[str] = Field(default_factory=list)  # all md links in the body
    references: list[ConceptRef] = Field(default_factory=list)  # links that resolve
    created_at: str | None = None
    updated_at: str | None = None


class ConceptSummary(BaseModel):
    workspace_id: str
    path: str
    type: str
    title: str
    description: str | None = None
    runtime: str | None = None
    tags: list[str] = Field(default_factory=list)
    capabilities: list[str] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
