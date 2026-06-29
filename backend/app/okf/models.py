"""Result types for projecting an OKF bundle into the graph."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class IngestionResult:
    documents: int
    references: int
    orphans: list[str]
    embedded: int
    document_ids: list[str] = field(default_factory=list)
