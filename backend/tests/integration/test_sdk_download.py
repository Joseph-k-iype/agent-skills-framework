"""SDK download endpoint — public, no auth, serves built artifact with SHA-256 checksum.

Tests use monkeypatching to redirect the dist-path resolver so they
do NOT depend on a real `uv build` having been run.
"""

from __future__ import annotations

import hashlib
import shutil
import tempfile
from pathlib import Path

import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
import app.api.v1.routers.sdk as sdk_module

pytestmark = pytest.mark.asyncio


@pytest.fixture
def client():
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


@pytest.fixture
def temp_dist_dir(tmp_path: Path):
    """Return a temp directory that acts as sdk/python/dist/ with one wheel."""
    dist = tmp_path / "dist"
    dist.mkdir()
    artifact = dist / "eakso-0.1.0-py3-none-any.whl"
    artifact.write_bytes(b"FAKE WHEEL CONTENT FOR TESTING")
    return dist


@pytest.fixture
def empty_dist_dir(tmp_path: Path):
    """Return a temp directory that is entirely empty (no artifacts)."""
    dist = tmp_path / "dist_empty"
    dist.mkdir()
    return dist


@pytest.fixture
def missing_dist_dir(tmp_path: Path):
    """Return a path that does NOT exist."""
    return tmp_path / "dist_nonexistent"


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------

async def test_download_returns_200_with_artifact(client, temp_dist_dir, monkeypatch):
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: temp_dist_dir)

    resp = await client.get("/api/v1/sdk/download")

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/octet-stream"


async def test_download_content_disposition_is_attachment(client, temp_dist_dir, monkeypatch):
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: temp_dist_dir)

    resp = await client.get("/api/v1/sdk/download")

    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd


async def test_download_checksum_header_matches_file(client, temp_dist_dir, monkeypatch):
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: temp_dist_dir)

    # Compute expected SHA-256
    artifact = max(temp_dist_dir.iterdir(), key=lambda p: p.stat().st_mtime)
    expected_sha = hashlib.sha256(artifact.read_bytes()).hexdigest()

    resp = await client.get("/api/v1/sdk/download")

    assert resp.status_code == 200
    assert resp.headers.get("x-checksum-sha256") == expected_sha


async def test_download_body_matches_artifact(client, temp_dist_dir, monkeypatch):
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: temp_dist_dir)

    artifact = max(temp_dist_dir.iterdir(), key=lambda p: p.stat().st_mtime)

    resp = await client.get("/api/v1/sdk/download")

    assert resp.content == artifact.read_bytes()


# ---------------------------------------------------------------------------
# Degraded / missing artifact
# ---------------------------------------------------------------------------

async def test_download_503_when_dist_is_empty(client, empty_dist_dir, monkeypatch):
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: empty_dist_dir)

    resp = await client.get("/api/v1/sdk/download")

    assert resp.status_code == 503
    body = resp.json()
    assert body["ok"] is False
    assert "reason" in body


async def test_download_503_when_dist_missing(client, missing_dist_dir, monkeypatch):
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: missing_dist_dir)

    resp = await client.get("/api/v1/sdk/download")

    assert resp.status_code == 503
    body = resp.json()
    assert body["ok"] is False


# ---------------------------------------------------------------------------
# Public — no auth required
# ---------------------------------------------------------------------------

async def test_download_requires_no_auth(client, temp_dist_dir, monkeypatch):
    """Endpoint must work with zero Authorization header."""
    monkeypatch.setattr(sdk_module, "_resolve_dist_dir", lambda: temp_dist_dir)

    resp = await client.get("/api/v1/sdk/download")
    # If auth were required without a key, this would be 401/403.
    assert resp.status_code == 200
