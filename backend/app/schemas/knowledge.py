from __future__ import annotations

from pydantic import BaseModel, Field


class OkfImportRequest(BaseModel):
    source_repository: str = Field(min_length=1)
    workspace_id: str | None = None
    folder_id: str | None = None


class OkfImportResult(BaseModel):
    documents: int
    references: int
    embedded: int
    orphans: list[str]
    document_ids: list[str]
