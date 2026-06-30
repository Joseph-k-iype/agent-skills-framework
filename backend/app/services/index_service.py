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
            vectors, is_real = await self.provider.embed_checked(
                [c.embedding_text() for c in concepts]
            )
            for c, vec in zip(concepts, vectors, strict=True):
                if is_real:
                    self.repo.set_embedding(workspace_id=workspace_id, path=c.path, vec=vec)
                    embedded += 1
                else:
                    # Degraded fallback (e.g. rate-limited) — leave it pending for
                    # the heal pass rather than poisoning search with a hash vector.
                    self.repo.mark_embedding_pending(workspace_id=workspace_id, path=c.path)

        # Rebuild published-version nodes from git tags (cleared above).
        self.rebuild_versions(workspace_id, bundle)

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
        # Rebuild this node's outgoing references from scratch so renamed/removed
        # links don't leave stale edges behind.
        self.repo.clear_references_from(workspace_id=workspace_id, path=c.path)
        valid = {p for p in bundle.list_files(".md") if not is_reserved(p)}
        for link in c.links:
            if link in valid:
                self.repo.create_reference(
                    workspace_id=workspace_id, from_path=c.path, to_path=link
                )
        vec, is_real = await self.provider.embed_one_checked(c.embedding_text())
        if is_real:
            self.repo.set_embedding(workspace_id=workspace_id, path=path, vec=vec)
        else:
            self.repo.mark_embedding_pending(workspace_id=workspace_id, path=path)

    async def embed_pending(self, workspace_id: str) -> int:
        """Re-embed every node whose embedding is missing/degraded. Returns count healed.

        Safe to call repeatedly (idempotent) and off the request path — used both by
        the post-save background heal and the manual reindex button.
        """
        paths = self.repo.pending_embedding_paths(workspace_id)
        if not paths:
            return 0
        bundle = BundleRepo(workspace_id)
        if not bundle.exists:
            return 0
        healed = 0
        for path in paths:
            if is_reserved(path) or not bundle.exists_file(path):
                continue
            c = parse_concept(path, bundle.read_file(path))
            vec, is_real = await self.provider.embed_one_checked(c.embedding_text())
            if is_real:
                self.repo.set_embedding(workspace_id=workspace_id, path=path, vec=vec)
                healed += 1
        if healed:
            log.info("embeddings_healed", workspace_id=workspace_id, healed=healed)
        return healed

    @staticmethod
    def _parse_publish_tag(subject: str) -> tuple[str, str] | None:
        """``publish <path> v<version>`` → ``(path, version)`` (else None)."""
        prefix = "publish "
        if not subject.startswith(prefix) or " v" not in subject:
            return None
        path, version = subject[len(prefix) :].rsplit(" v", 1)
        path, version = path.strip(), version.strip()
        return (path, version) if path and version else None

    def rebuild_versions(self, workspace_id: str, bundle: BundleRepo | None = None) -> int:
        """Recreate Version nodes from publish tags (so they survive a reindex)."""
        bundle = bundle or BundleRepo(workspace_id)
        if not bundle.exists:
            return 0
        count = 0
        for tag in bundle.list_tags():
            parsed = self._parse_publish_tag(tag["subject"])
            if not parsed:
                continue
            path, version = parsed
            self.repo.upsert_version(
                workspace_id=workspace_id,
                path=path,
                version=version,
                tag=tag["name"],
                ts=tag["ts"],
            )
            count += 1
        return count

    def remove_concept(self, workspace_id: str, path: str) -> None:
        self.repo.delete_concept(workspace_id=workspace_id, path=path)
