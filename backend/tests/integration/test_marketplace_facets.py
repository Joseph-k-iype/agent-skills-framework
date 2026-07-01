"""Faceted marketplace browse — capability and source filters.

Publishes two listings with differing capabilities/sources, then asserts:
- public_list(capability="extraction") returns only the matching listing
- combined capability+source filter works
- no-match filter returns []
"""

from __future__ import annotations

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.services.concept_service import ConceptService
from app.services.marketplace_service import MarketplaceService
from app.storage import paths

pytestmark = pytest.mark.asyncio


@pytest.fixture
async def admin_id() -> str:
    from app.repositories.user_repo import UserRepository

    async with SessionLocal() as db:
        user = await UserRepository(db).get_by_username("admin")
        assert user is not None, "run `make seed` before integration tests"
        return str(user.id)


@pytest.fixture
def setup(monkeypatch, tmp_path, graph_name):
    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    if not client.ping():
        pytest.skip("FalkorDB not available")
    from app.graph.indexes import bootstrap_indexes

    bootstrap_indexes()


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


async def test_capability_filter_returns_matching_listing(setup, admin_id):
    """public_list(capability="extraction") returns only the listing with that capability."""
    async with SessionLocal() as db:
        u = _user(admin_id)
        cs = ConceptService(db, u)

        # Listing A: has "extraction" capability, source "web"
        await cs.create(
            workspace_id="facet_ws_a",
            folder_path="",
            name="Web Extractor",
            type="skill",
            description="extracts from web",
            runtime=None,
            tags=["web"],
            capabilities=["extraction", "parsing"],
            sources=["web"],
            body="# Web Extractor\nExtracts content.",
            frontmatter={},
        )
        await cs.publish(workspace_id="facet_ws_a", path="web-extractor.md", version="1.0.0")

        # Listing B: no "extraction" capability, different source
        await cs.create(
            workspace_id="facet_ws_b",
            folder_path="",
            name="Data Summarizer",
            type="skill",
            description="summarizes data",
            runtime=None,
            tags=["data"],
            capabilities=["summarization"],
            sources=["database"],
            body="# Data Summarizer\nSummarizes content.",
            frontmatter={},
        )
        await cs.publish(workspace_id="facet_ws_b", path="data-summarizer.md", version="1.0.0")

        await db.commit()

    async with SessionLocal() as db:
        mp = MarketplaceService(db, None)
        results = await mp.public_list(capability="extraction")
        titles = [r["title"] for r in results]
        assert "Web Extractor" in titles, f"Expected 'Web Extractor' in {titles}"
        assert "Data Summarizer" not in titles, f"'Data Summarizer' should not appear in {titles}"


async def test_combined_capability_and_source_filter(setup, admin_id):
    """Combined capability+source filter returns only the listing matching both."""
    async with SessionLocal() as db:
        u = _user(admin_id)
        cs = ConceptService(db, u)

        # Listing C: capability "classification", source "internal"
        await cs.create(
            workspace_id="facet_ws_c",
            folder_path="",
            name="Internal Classifier",
            type="skill",
            description="classifies internal data",
            runtime=None,
            tags=[],
            capabilities=["classification"],
            sources=["internal"],
            body="# Internal Classifier\nClassifies.",
            frontmatter={},
        )
        await cs.publish(workspace_id="facet_ws_c", path="internal-classifier.md", version="1.0.0")

        # Listing D: capability "classification", source "external"
        await cs.create(
            workspace_id="facet_ws_d",
            folder_path="",
            name="External Classifier",
            type="skill",
            description="classifies external data",
            runtime=None,
            tags=[],
            capabilities=["classification"],
            sources=["external"],
            body="# External Classifier\nClassifies.",
            frontmatter={},
        )
        await cs.publish(workspace_id="facet_ws_d", path="external-classifier.md", version="1.0.0")

        await db.commit()

    async with SessionLocal() as db:
        mp = MarketplaceService(db, None)
        # Both share "classification" capability
        cap_results = await mp.public_list(capability="classification")
        cap_titles = [r["title"] for r in cap_results]
        assert "Internal Classifier" in cap_titles
        assert "External Classifier" in cap_titles

        # source="internal" narrows to only Internal Classifier
        both_results = await mp.public_list(capability="classification", source="internal")
        both_titles = [r["title"] for r in both_results]
        assert "Internal Classifier" in both_titles
        assert "External Classifier" not in both_titles


async def test_no_match_returns_empty_list(setup, admin_id):
    """A facet filter with no matching listing returns [] not an error."""
    async with SessionLocal() as db:
        mp = MarketplaceService(db, None)
        results = await mp.public_list(capability="nonexistent_capability_xyz_12345")
        assert results == []

        results2 = await mp.public_list(source="nonexistent_source_xyz_12345")
        assert results2 == []
