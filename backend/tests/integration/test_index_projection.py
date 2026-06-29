"""Project a workspace bundle into FalkorDB and keep it in sync."""

from __future__ import annotations

import pytest

from app.graph import client
from app.repositories.concept_graph_repo import ConceptGraphRepository
from app.services.index_service import IndexService
from app.storage.repo import BundleRepo

pytestmark = pytest.mark.asyncio

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
