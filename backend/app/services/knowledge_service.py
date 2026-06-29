"""Semantic search pipeline: embed query → vector search → graph-expand → rank.

Every result carries provenance (the originating OKF document + the references it
links to) per the PRD explainability rule — no graph-derived answer without it.
"""

from __future__ import annotations

from app.llm.provider import get_provider
from app.repositories.okf_graph_repo import OkfGraphRepository


class KnowledgeService:
    def __init__(self) -> None:
        self.repo = OkfGraphRepository()
        self.llm = get_provider()

    async def search(self, query: str, k: int = 10) -> dict:
        vec = await self.llm.embed_one(query)
        hits = self.repo.search(embedding=vec, k=k)
        results = []
        for props, score in hits:
            doc = self.repo.get_document(props.get("id", "")) or props
            results.append(
                {
                    "id": doc.get("id"),
                    "title": doc.get("title"),
                    "type": doc.get("type"),
                    "relative_path": doc.get("relative_path"),
                    "score": round(float(score), 6),
                    "provenance": {
                        "source_repository": doc.get("source_repository"),
                        "references": doc.get("references", []),
                        "folder_id": doc.get("folder_id"),
                    },
                }
            )
        return {
            "query": query,
            "semantic": self.llm.using_real_embeddings,
            "results": results,
        }

    def get_document(self, doc_id: str) -> dict | None:
        return self.repo.get_document(doc_id)

    def list_documents(self, workspace_id: str | None) -> list[dict]:
        return self.repo.list_documents(workspace_id=workspace_id)

    def neighborhood(self, node_id: str) -> dict | None:
        return self.repo.neighborhood(node_id)
