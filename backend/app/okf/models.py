"""Pure data structures for parsed OKF documents."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class OkfDocument:
    id: str
    title: str
    type: str
    relative_path: str
    body: str
    tags: list[str] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    # Raw link targets found in the body (wikilink titles or relative md paths).
    raw_links: list[str] = field(default_factory=list)
    # Resolved after linking: ids of referenced documents.
    references: list[str] = field(default_factory=list)

    def embedding_text(self) -> str:
        """The text fed to the embedding model — title, tags, then body."""
        tagline = " ".join(self.tags)
        return f"{self.title}\n{tagline}\n{self.body}".strip()


@dataclass
class IngestionResult:
    documents: int
    references: int
    orphans: list[str]
    embedded: int
    document_ids: list[str] = field(default_factory=list)
