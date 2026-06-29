"""Integration test: OKF ingestion + vector search against real FalkorDB.

Forces the offline (local) embedding path so the test is deterministic and needs
no network / API key.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.core.config import settings
from app.graph.indexes import bootstrap_indexes
from app.services.knowledge_service import KnowledgeService
from app.services.okf_service import OkfService

SAMPLE = Path(__file__).resolve().parents[3] / "scripts" / "seed_okf_sample"


@pytest.fixture
def offline_embeddings(monkeypatch):
    monkeypatch.setattr(settings, "openrouter_api_key", "", raising=False)


async def test_ingest_and_search(graph_name, offline_embeddings):
    bootstrap_indexes()  # create vector + range indexes on the test graph

    result = await OkfService().ingest(
        source_repository=str(SAMPLE), workspace_id=None, folder_id=None
    )
    assert result.documents == 4
    assert result.references == 4
    assert "nonexistent-spec.md" in result.orphans

    # Re-ingest is idempotent for embeddings (content-hash dedupe).
    again = await OkfService().ingest(
        source_repository=str(SAMPLE), workspace_id=None, folder_id=None
    )
    assert again.embedded == 0

    # Lexical search should surface the revenue policy for a revenue query.
    res = await KnowledgeService().search("how is revenue recognized", k=4)
    titles = [r["title"] for r in res["results"]]
    assert "Revenue Recognition Policy" in titles
    top = res["results"][0]
    assert "references" in top["provenance"]


async def test_neighborhood_has_reference_edges(graph_name, offline_embeddings):
    bootstrap_indexes()
    await OkfService().ingest(source_repository=str(SAMPLE), workspace_id=None, folder_id=None)

    hood = KnowledgeService().neighborhood("revenue-recognition")
    assert hood is not None
    rels = {e["rel"] for e in hood["edges"]}
    assert "REFERENCES" in rels
