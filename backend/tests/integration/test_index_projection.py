"""Project a workspace bundle into FalkorDB and keep it in sync."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.graph import client
from app.llm.providers.local import local_embedding
from app.repositories.concept_graph_repo import ConceptGraphRepository
from app.services.index_service import IndexService
from app.storage.repo import BundleRepo

pytestmark = pytest.mark.asyncio


class FakeProvider:
    """Real-or-degraded embeddings on demand, to exercise the heal path offline."""

    using_real_embeddings = True

    def __init__(self, real: bool) -> None:
        self.real = real

    async def embed_checked(self, texts):
        return [local_embedding(t, settings.embedding_dim) for t in texts], self.real

    async def embed_one_checked(self, text):
        vecs, is_real = await self.embed_checked([text])
        return vecs[0], is_real

SKILL = """---
type: skill
title: Invoice OCR
runtime: python 3.12
---
# OCR

Uses [the validator](validator.md).
"""

VALIDATOR = """---
type: agent
title: Validator
---
# Validates invoices
"""


@pytest.fixture
def workspace(monkeypatch, tmp_path, graph_name):
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes

    bootstrap_indexes()  # vector + range indexes, as in production startup
    bundle = BundleRepo.init("wsX")
    bundle.write_file("payments/invoice-ocr.md", SKILL, "add skill", "admin")
    bundle.write_file("payments/validator.md", VALIDATOR, "add validator", "admin")
    return "wsX"


async def test_reindex_projects_nodes_and_reference_edge(workspace):
    result = await IndexService().reindex_workspace(workspace)
    assert result.documents == 2
    assert result.references == 1
    repo = ConceptGraphRepository()
    assert repo.count(workspace) == 2
    assert repo.count_references(workspace) == 1


async def test_reindex_is_idempotent(workspace):
    svc = IndexService()
    await svc.reindex_workspace(workspace)
    await svc.reindex_workspace(workspace)
    repo = ConceptGraphRepository()
    assert repo.count(workspace) == 2  # no duplicates
    assert repo.count_references(workspace) == 1


async def test_remove_concept_drops_node(workspace):
    svc = IndexService()
    await svc.reindex_workspace(workspace)
    svc.remove_concept(workspace, "payments/validator.md")
    repo = ConceptGraphRepository()
    assert repo.count(workspace) == 1


async def test_get_concept_returns_references(workspace):
    await IndexService().reindex_workspace(workspace)
    repo = ConceptGraphRepository()
    doc = repo.get_concept(workspace_id=workspace, path="payments/invoice-ocr.md")
    assert doc is not None
    assert doc["runtime"] == "python 3.12"
    assert any(r["path"] == "payments/validator.md" for r in doc["references"])


async def test_degraded_embeddings_are_pending_excluded_then_healed(workspace):
    repo = ConceptGraphRepository()
    svc = IndexService()

    # Simulate a rate-limited reindex: every embedding is a degraded fallback.
    svc.provider = FakeProvider(real=False)
    await svc.reindex_workspace(workspace)
    assert set(repo.pending_embedding_paths(workspace)) == {
        "payments/invoice-ocr.md",
        "payments/validator.md",
    }
    # Degraded nodes are not searchable (no real vector persisted).
    q = local_embedding("invoice ocr", settings.embedding_dim)
    assert repo.search(workspace_id=workspace, embedding=q, k=10) == []

    # Heal with a working provider: pending nodes get real embeddings.
    svc.provider = FakeProvider(real=True)
    healed = await svc.embed_pending(workspace)
    assert healed == 2
    assert repo.pending_embedding_paths(workspace) == []

    # Now they rank in search.
    hits = repo.search(workspace_id=workspace, embedding=q, k=10)
    assert any(h[0]["path"] == "payments/invoice-ocr.md" for h in hits)


async def test_publish_projects_version_node_into_graph(workspace):
    svc = IndexService()
    await svc.reindex_workspace(workspace)
    bundle = BundleRepo(workspace)
    bundle.tag("payments-invoice-ocr-v1.0.0", "publish payments/invoice-ocr.md v1.0.0")
    assert svc.rebuild_versions(workspace, bundle) == 1

    repo = ConceptGraphRepository()
    versions = repo.versions_for(workspace_id=workspace, path="payments/invoice-ocr.md")
    assert [v["version"] for v in versions] == ["1.0.0"]
    # The graph node surfaces the version count for the explorer badge.
    node = next(n for n in repo.graph(workspace)["nodes"] if n["path"] == "payments/invoice-ocr.md")
    assert node["versions"] == 1


async def test_reindex_rebuilds_version_nodes_from_tags(workspace):
    svc = IndexService()
    await svc.reindex_workspace(workspace)
    BundleRepo(workspace).tag("payments-validator-v2.0.0", "publish payments/validator.md v2.0.0")
    # A full reindex clears the projection and must rebuild versions from git tags.
    await svc.reindex_workspace(workspace)
    repo = ConceptGraphRepository()
    versions = repo.versions_for(workspace_id=workspace, path="payments/validator.md")
    assert [v["version"] for v in versions] == ["2.0.0"]


async def test_reindex_clears_stale_reference_edges(workspace):
    svc = IndexService()
    await svc.reindex_workspace(workspace)
    repo = ConceptGraphRepository()
    assert repo.count_references(workspace) == 1

    # Drop the link from the skill body; re-indexing that file must remove the edge.
    BundleRepo(workspace).write_file(
        "payments/invoice-ocr.md",
        "---\ntype: skill\ntitle: Invoice OCR\n---\n# OCR\n\nNo links now.\n",
        "drop link",
        "admin",
    )
    await svc.index_concept(workspace, "payments/invoice-ocr.md")
    assert repo.count_references(workspace) == 0
