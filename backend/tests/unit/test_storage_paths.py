"""Filesystem path helpers for git-backed workspace bundles."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.storage import paths


def test_slugify():
    assert paths.slugify("My Skill!") == "my-skill"
    assert paths.slugify("  Finance / Payments  ") == "finance-payments"
    assert paths.slugify("already-kebab") == "already-kebab"


def test_workspace_root_under_configured_root(monkeypatch, tmp_path):
    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    root = paths.workspace_root("ws123")
    assert root == Path(tmp_path) / "ws123"


def test_safe_join_keeps_inside_root(tmp_path):
    target = paths.safe_join(tmp_path, "a", "b.md")
    assert target == (tmp_path / "a" / "b.md").resolve()


def test_safe_join_rejects_traversal(tmp_path):
    with pytest.raises(ValueError):
        paths.safe_join(tmp_path, "../escape.md")
    with pytest.raises(ValueError):
        paths.safe_join(tmp_path, "a/../../escape.md")
