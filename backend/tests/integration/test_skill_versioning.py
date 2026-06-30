"""SHA-aware publish: immutable SkillVersion rows + idempotent re-publish."""

from __future__ import annotations

import uuid

import pytest

from app.api.deps import CurrentUser
from app.auth.rbac import RoleName, permissions_for
from app.db.session import SessionLocal
from app.graph import client
from app.okf.canonical import content_sha
from app.okf.concept import parse_concept
from app.services.concept_service import ConceptService
from app.services.marketplace_service import MarketplaceService
from app.storage import paths
from app.storage.repo import BundleRepo

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


def _user(admin_id: str) -> CurrentUser:
    return CurrentUser(
        id=admin_id, role=RoleName.DEVELOPER, permissions=permissions_for("developer")
    )


@pytest.fixture
async def make_service_with_listing(setup, admin_id):
    """A MarketplaceService against a real DB session, with a listing already
    published once (so version 1 exists), plus the frontmatter/body used to
    compute its content SHA."""
    ws = "ws_" + uuid.uuid4().hex[:8]
    async with SessionLocal() as db:
        u = _user(admin_id)
        cs = ConceptService(db, u)
        out = await cs.create(
            workspace_id=ws,
            folder_path="",
            name="Lineage Tracker",
            type="skill",
            description="tracks lineage",
            runtime=None,
            tags=["data"],
            capabilities=[],
            body="# Lineage\nTrack origins.",
            frontmatter={},
        )
        path = out.path
        await cs.publish(workspace_id=ws, path=path, version="1.0.0")

        # Use the raw parsed concept (full frontmatter), matching exactly what
        # MarketplaceService.upsert_on_publish hashes — ConceptOut.frontmatter
        # only carries *unknown* keys, not the full metadata dict.
        bundle = BundleRepo(ws)
        concept = parse_concept(path, bundle.read_file(path))

        svc = MarketplaceService(db, u)
        listings = await svc.list_listings(q=None, type=None)
        listing = next(
            x
            for x in listings
            if x["source_path"] == path and x["source_workspace_id"] == ws
        )
        listing_id = listing["id"]

        yield svc, listing_id, concept.frontmatter, concept.body
        await db.commit()


async def test_publish_is_idempotent_on_identical_content(make_service_with_listing):
    """Re-publishing identical content must not create a second version."""
    svc, listing_id, frontmatter, body = make_service_with_listing
    sha = content_sha(frontmatter, body)

    v1 = await svc.repo.version_for_sha(uuid.UUID(listing_id), sha)
    assert v1 is not None and v1.version == 1

    # Same SHA -> no new version.
    next_n = await svc.repo.next_version_number(uuid.UUID(listing_id))
    assert next_n == 2  # would be the next number IF content changed
    existing = await svc.repo.get_version_by_sha(sha)
    assert existing is not None

    # Re-publishing identical content is idempotent: no second version created.
    versions_before = await svc.repo.list_versions(uuid.UUID(listing_id))
    assert len(versions_before) == 1

    listing_obj = await svc.repo.get(uuid.UUID(listing_id))
    await svc.upsert_on_publish(
        workspace_id=listing_obj.source_workspace_id,
        path=listing_obj.source_path,
        version="1.0.0",
    )

    versions_after = await svc.repo.list_versions(uuid.UUID(listing_id))
    assert len(versions_after) == 1
    assert [v.version for v in versions_after] == [1]
