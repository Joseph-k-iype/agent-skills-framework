"""Project a workspace bundle (markdown files) into the FalkorDB graph.

This is the only writer of the Concept projection. Files are the source of truth;
``reindex_workspace`` rebuilds the projection from scratch (idempotent), while
``index_concept`` / ``remove_concept`` keep it in sync on single-file edits.
Embeddings are content-hash deduped so unchanged files are not re-embedded.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import PurePosixPath

from app.core.logging import get_logger
from app.llm.provider import get_provider
from app.okf.concept import Concept, parse_concept
from app.okf.models import IngestionResult
from app.repositories.concept_graph_repo import ConceptGraphRepository
from app.storage.repo import BundleRepo

log = get_logger("index")

_RESERVED = {"index.md", "log.md"}


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def is_reserved(path: str) -> bool:
    return PurePosixPath(path).name in _RESERVED


class IndexService:
    def __init__(self) -> None:
        self.repo = ConceptGraphRepository()
        self.provider = get_provider()

    def _load_concepts(self, bundle: BundleRepo) -> list[Concept]:
        concepts: list[Concept] = []
        for path in bundle.list_files(".md"):
            if is_reserved(path):
                continue
            concepts.append(parse_concept(path, bundle.read_file(path)))
        return concepts

    def _upsert(self, workspace_id: str, c: Concept, ts: str) -> None:
        self.repo.upsert_concept(
            workspace_id=workspace_id,
            path=c.path,
            title=c.title,
            type=c.type,
            description=c.description,
            runtime=c.runtime,
            tags=c.tags,
            capabilities=c.capabilities,
            body=c.body,
            content_hash=_hash(c.embedding_text()),
            ts=ts,
        )

    async def reindex_workspace(self, workspace_id: str) -> IngestionResult:
        bundle = BundleRepo(workspace_id)
        if not bundle.exists:
            return IngestionResult(documents=0, references=0, orphans=[], embedded=0)

        self.repo.clear_workspace(workspace_id)
        concepts = self._load_concepts(bundle)
        ts = _now()

        for c in concepts:
            self._upsert(workspace_id, c, ts)

        valid = {c.path for c in concepts}
        ref_count = 0
        orphans: list[str] = []
        for c in concepts:
            for link in c.links:
                if link in valid:
                    self.repo.create_reference(
                        workspace_id=workspace_id, from_path=c.path, to_path=link
                    )
                    ref_count += 1
                else:
                    orphans.append(f"{c.path} -> {link}")

        embedded = 0
        if concepts:
            vectors = await self.provider.embed([c.embedding_text() for c in concepts])
            for c, vec in zip(concepts, vectors, strict=True):
                self.repo.set_embedding(workspace_id=workspace_id, path=c.path, vec=vec)
                embedded += 1

        log.info(
            "workspace_reindexed",
            workspace_id=workspace_id,
            documents=len(concepts),
            references=ref_count,
            orphans=len(orphans),
            embedded=embedded,
            real_embeddings=self.provider.using_real_embeddings,
        )
        return IngestionResult(
            documents=len(concepts),
            references=ref_count,
            orphans=orphans,
            embedded=embedded,
            document_ids=[c.path for c in concepts],
        )

    async def index_concept(self, workspace_id: str, path: str) -> None:
        """Index (or re-index) a single file, refreshing its outgoing references."""
        if is_reserved(path):
            return
        bundle = BundleRepo(workspace_id)
        c = parse_concept(path, bundle.read_file(path))
        ts = _now()
        self._upsert(workspace_id, c, ts)
        valid = {p for p in bundle.list_files(".md") if not is_reserved(p)}
        for link in c.links:
            if link in valid:
                self.repo.create_reference(
                    workspace_id=workspace_id, from_path=c.path, to_path=link
                )
        vec = await self.provider.embed_one(c.embedding_text())
        self.repo.set_embedding(workspace_id=workspace_id, path=path, vec=vec)

    def remove_concept(self, workspace_id: str, path: str) -> None:
        self.repo.delete_concept(workspace_id=workspace_id, path=path)
