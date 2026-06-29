"""OKF ingestion: discover → parse → link → graph upsert → embed.

Runs synchronously for responsiveness on small knowledge sets; the Celery task
``okf.ingest_repo`` wraps the same coroutine for large/background imports.
Embeddings are content-hash deduped so unchanged documents are not re-embedded.
"""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path

from app.core.logging import get_logger
from app.llm.provider import get_provider
from app.okf.linker import resolve_links
from app.okf.models import IngestionResult, OkfDocument
from app.okf.parser import parse_document
from app.repositories.okf_graph_repo import OkfGraphRepository

log = get_logger("okf")


def _now() -> str:
    return datetime.now(UTC).isoformat()


def _hash(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


def discover(source_repository: str) -> list[OkfDocument]:
    root = Path(source_repository).expanduser().resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"OKF source is not a directory: {source_repository}")
    docs: list[OkfDocument] = []
    for path in sorted(root.rglob("*.md")):
        rel = str(path.relative_to(root))
        docs.append(parse_document(rel, path.read_text(encoding="utf-8")))
    return docs


class OkfService:
    def __init__(self) -> None:
        self.repo = OkfGraphRepository()
        self.llm = get_provider()

    async def ingest(
        self, *, source_repository: str, workspace_id: str | None, folder_id: str | None
    ) -> IngestionResult:
        docs = discover(source_repository)
        orphans = resolve_links(docs)
        ts = _now()

        # 1) upsert nodes + folder links; decide which need (re)embedding
        to_embed: list[OkfDocument] = []
        for d in docs:
            content_hash = _hash(d.embedding_text())
            prev = self.repo.existing_hash(d.id)
            self.repo.upsert_document(
                id=d.id,
                title=d.title,
                type=d.type,
                relative_path=d.relative_path,
                source_repository=source_repository,
                body=d.body,
                tags=d.tags,
                workspace_id=workspace_id,
                content_hash=content_hash,
                ts=ts,
            )
            if folder_id:
                self.repo.link_to_folder(id=d.id, folder_id=folder_id)
            if prev != content_hash:
                to_embed.append(d)

        # 2) reference edges
        ref_count = 0
        for d in docs:
            for target in d.references:
                self.repo.create_reference(from_id=d.id, to_id=target)
                ref_count += 1

        # 3) embeddings (batched), skipping unchanged docs
        embedded = 0
        if to_embed:
            vectors = await self.llm.embed([d.embedding_text() for d in to_embed])
            for d, vec in zip(to_embed, vectors, strict=True):
                self.repo.set_embedding(id=d.id, vec=vec)
                embedded += 1

        log.info(
            "okf_ingested",
            documents=len(docs),
            references=ref_count,
            orphans=len(orphans),
            embedded=embedded,
            real_embeddings=self.llm.using_real_embeddings,
        )
        return IngestionResult(
            documents=len(docs),
            references=ref_count,
            orphans=orphans,
            embedded=embedded,
            document_ids=[d.id for d in docs],
        )
