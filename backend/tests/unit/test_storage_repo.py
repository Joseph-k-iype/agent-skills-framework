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


def test_rewrite_identical_content_is_idempotent(repo):
    """Re-saving byte-identical content must not crash on an empty commit."""
    sha1 = repo.write_file("a/x.md", "# same", "add x", "admin")
    sha2 = repo.write_file("a/x.md", "# same", "noop edit", "admin")
    # No new commit is created when nothing changed; HEAD is unchanged.
    assert sha2 == sha1
    assert len(repo.history("a/x.md")) == 1


def test_add_dir_twice_is_idempotent(repo):
    """Re-adding an existing directory must not crash on an empty commit."""
    repo.add_dir("folder", "mk folder", "admin")
    repo.add_dir("folder", "mk folder again", "admin")


def test_git_error_surfaces_stderr(repo):
    """A failing git call must raise with git's stderr, not an opaque error."""
    with pytest.raises(RuntimeError) as exc:
        repo.delete_path("does/not/exist.md", "rm ghost", "admin")
    assert "git" in str(exc.value).lower()


def test_read_file_at_returns_old_content(repo):
    repo.write_file("a/x.md", "v1", "add", "admin")
    repo.write_file("a/x.md", "v2", "edit", "admin")
    assert repo.read_file_at("a/x.md", "HEAD~1") == "v1"
    assert repo.read_file_at("a/x.md", "HEAD") == "v2"


def test_diff_shows_change(repo):
    repo.write_file("a/x.md", "v1\n", "add", "admin")
    repo.write_file("a/x.md", "v2\n", "edit", "admin")
    d = repo.diff("a/x.md", "HEAD~1", "HEAD")
    assert "-v1" in d and "+v2" in d


def test_restore_reverts_as_new_commit(repo):
    repo.write_file("a/x.md", "v1", "add", "admin")
    repo.write_file("a/x.md", "v2", "edit", "admin")
    repo.restore("a/x.md", "HEAD~1", "restore to v1", "admin")
    assert repo.read_file("a/x.md") == "v1"  # content reverted
    hist = repo.history("a/x.md")
    assert len(hist) == 3 and hist[0]["message"] == "restore to v1"  # non-destructive


def test_list_tags_parses_publish_subject(repo):
    repo.write_file("a/x.md", "v1", "add", "admin")
    repo.tag("a-x-v1.0.0", "publish a/x.md v1.0.0")
    tags = repo.list_tags()
    assert any(
        t["name"] == "a-x-v1.0.0" and t["subject"] == "publish a/x.md v1.0.0" for t in tags
    )
