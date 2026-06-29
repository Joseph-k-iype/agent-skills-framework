"""Git-backed bundle repository: write/read/move/delete/history/tag."""

from __future__ import annotations

import pytest

from app.storage.repo import BundleRepo


@pytest.fixture
def repo(monkeypatch, tmp_path):
    from app.storage import paths

    monkeypatch.setattr(paths.settings, "workspaces_root", str(tmp_path), raising=False)
    return BundleRepo.init("ws1")


def test_init_creates_git_repo(repo, tmp_path):
    assert (tmp_path / "ws1" / ".git").is_dir()


def test_write_and_read_round_trip(repo):
    sha = repo.write_file("finance/payments/x.md", "# hi", "add x", "admin")
    assert isinstance(sha, str) and len(sha) >= 7
    assert repo.read_file("finance/payments/x.md") == "# hi"


def test_list_files_returns_markdown(repo):
    repo.write_file("a/x.md", "# x", "add x", "admin")
    repo.write_file("b/y.md", "# y", "add y", "admin")
    assert repo.list_files() == ["a/x.md", "b/y.md"]


def test_history_grows_with_commits(repo):
    repo.write_file("a/x.md", "v1", "add x", "admin")
    repo.write_file("a/x.md", "v2", "edit x", "admin")
    hist = repo.history("a/x.md")
    assert len(hist) == 2
    assert hist[0]["message"] == "edit x"  # newest first
    assert {"sha", "message", "author", "ts"} <= set(hist[0])


def test_move_relocates_file(repo):
    repo.write_file("a/x.md", "# x", "add x", "admin")
    repo.move_path("a/x.md", "b/x.md", "move x", "admin")
    assert repo.read_file("b/x.md") == "# x"
    assert repo.list_files() == ["b/x.md"]


def test_delete_removes_file(repo):
    repo.write_file("a/x.md", "# x", "add x", "admin")
    repo.delete_path("a/x.md", "rm x", "admin")
    assert repo.list_files() == []


def test_tag_does_not_raise(repo):
    repo.write_file("a/x.md", "# x", "add x", "admin")
    repo.tag("v0.1.0", "release")


def test_traversal_is_blocked(repo):
    with pytest.raises(ValueError):
        repo.write_file("../escape.md", "nope", "bad", "admin")
