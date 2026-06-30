"""Git-backed OKF bundle repository.

Each workspace is a git repo at ``<workspaces_root>/<workspace_id>``. The files
on disk are the source of truth; ``git`` provides version history (``history``),
and tags mark published versions. We shell out to ``git`` (no extra dependency)
and keep every path inside the bundle via :func:`app.storage.paths.safe_join`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

from app.core.logging import get_logger
from app.storage import paths

log = get_logger("storage")

_AUTHOR_EMAIL = "noreply@eakso.local"


class BundleRepo:
    def __init__(self, workspace_id: str) -> None:
        self.workspace_id = workspace_id
        self.root: Path = paths.workspace_root(workspace_id)

    # ── construction ──
    @classmethod
    def init(cls, workspace_id: str) -> BundleRepo:
        """Create (idempotently) the bundle directory and git repo."""
        repo = cls(workspace_id)
        repo.root.mkdir(parents=True, exist_ok=True)
        if not (repo.root / ".git").is_dir():
            repo._git("init", "-q")
            repo._git("config", "user.name", "EAKSO")
            repo._git("config", "user.email", _AUTHOR_EMAIL)
            # An empty initial commit so history/log always has a base.
            repo._git("commit", "-q", "--allow-empty", "-m", "init bundle")
        return repo

    @property
    def exists(self) -> bool:
        return (self.root / ".git").is_dir()

    # ── git plumbing ──
    def _git(self, *args: str, author: str | None = None) -> str:
        env = None
        if author is not None:
            import os

            env = {
                **os.environ,
                "GIT_AUTHOR_NAME": author,
                "GIT_AUTHOR_EMAIL": _AUTHOR_EMAIL,
                "GIT_COMMITTER_NAME": author,
                "GIT_COMMITTER_EMAIL": _AUTHOR_EMAIL,
            }
        result = subprocess.run(
            ["git", *args],
            cwd=str(self.root),
            check=False,
            capture_output=True,
            text=True,
            env=env,
        )
        if result.returncode != 0:
            # Surface git's own message; a bare CalledProcessError hides stderr.
            detail = (result.stderr or result.stdout or "").strip()
            raise RuntimeError(f"git {args[0]} failed (exit {result.returncode}): {detail}")
        return result.stdout.strip()

    def _abs(self, rel_path: str) -> Path:
        return paths.safe_join(self.root, rel_path)

    def _head(self) -> str:
        return self._git("rev-parse", "HEAD")

    def _has_staged_changes(self) -> bool:
        """True when the index differs from HEAD (``git diff --cached`` exits 1)."""
        result = subprocess.run(
            ["git", "diff", "--cached", "--quiet"],
            cwd=str(self.root),
            capture_output=True,
            text=True,
        )
        return result.returncode != 0

    def _commit(self, message: str, author: str) -> str:
        """Commit staged changes, or no-op when nothing is staged. Returns HEAD.

        Saving byte-identical content stages nothing; ``git commit`` would then
        exit non-zero with "nothing to commit". We treat that as success and
        return the unchanged HEAD so writes are idempotent.
        """
        if self._has_staged_changes():
            self._git("commit", "-q", "-m", message, author=author)
        return self._head()

    # ── directory operations ──
    def make_dir(self, rel_path: str) -> None:
        """Create a directory (tracked via a .gitkeep placeholder, no commit)."""
        target = self._abs(rel_path)
        target.mkdir(parents=True, exist_ok=True)
        keep = target / ".gitkeep"
        if not keep.exists():
            keep.write_text("", encoding="utf-8")

    def dir_exists(self, rel_path: str) -> bool:
        return self._abs(rel_path).is_dir()

    def add_dir(self, rel_path: str, message: str, author: str) -> str:
        """Create a directory and commit its .gitkeep so empty folders persist."""
        self.make_dir(rel_path)
        self._git("add", "-A")
        return self._commit(message, author)

    def move_dir(self, src: str, dst: str, message: str, author: str) -> str:
        """Move a directory tree (with all tracked files) and commit."""
        import shutil

        src_abs = self._abs(src)
        dst_abs = self._abs(dst)
        dst_abs.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_abs), str(dst_abs))
        self._git("add", "-A")
        return self._commit(message, author)

    def delete_dir(self, rel_path: str, message: str, author: str) -> str:
        """Remove a directory tree and commit."""
        import shutil

        target = self._abs(rel_path)
        if target.is_dir():
            shutil.rmtree(target)
        self._git("add", "-A")
        return self._commit(message, author)

    def write_file(self, rel_path: str, content: str, message: str, author: str) -> str:
        target = self._abs(rel_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content, encoding="utf-8")
        self._git("add", "--", rel_path)
        return self._commit(message, author)

    def read_file(self, rel_path: str) -> str:
        return self._abs(rel_path).read_text(encoding="utf-8")

    def exists_file(self, rel_path: str) -> bool:
        return self._abs(rel_path).is_file()

    def delete_path(self, rel_path: str, message: str, author: str) -> str:
        self._abs(rel_path)  # validate containment
        self._git("rm", "-q", "-r", "--", rel_path)
        return self._commit(message, author)

    def move_path(self, src: str, dst: str, message: str, author: str) -> str:
        self._abs(src)
        dst_abs = self._abs(dst)
        dst_abs.parent.mkdir(parents=True, exist_ok=True)
        self._git("mv", "--", src, dst)
        return self._commit(message, author)

    def list_files(self, suffix: str = ".md") -> list[str]:
        out = self._git("ls-files")
        files = [line for line in out.splitlines() if line and line.endswith(suffix)]
        return sorted(files)

    def history(self, rel_path: str | None = None) -> list[dict]:
        args = ["log", "--pretty=format:%H%x1f%an%x1f%aI%x1f%s"]
        if rel_path is not None:
            self._abs(rel_path)
            args += ["--", rel_path]
        out = self._git(*args)
        entries: list[dict] = []
        for line in out.splitlines():
            if not line:
                continue
            sha, author, ts, message = line.split("\x1f", 3)
            entries.append({"sha": sha, "author": author, "ts": ts, "message": message})
        return entries

    def tag(self, name: str, message: str) -> None:
        # Force so re-publishing the same version updates the tag.
        self._git("tag", "-f", "-a", name, "-m", message)

    def list_tags(self) -> list[dict]:
        """Annotated tags with their subject line + creation time (newest first).

        Publish tags carry a ``publish <path> v<version>`` subject, which the
        indexer parses to rebuild Version nodes after a projection rebuild.
        """
        fmt = "%(refname:short)%1f%(contents:subject)%1f%(creatordate:iso-strict)"
        out = self._git("for-each-ref", "--sort=-creatordate", "refs/tags", f"--format={fmt}")
        tags: list[dict] = []
        for line in out.splitlines():
            if not line:
                continue
            name, subject, ts = line.split("\x1f", 2)
            tags.append({"name": name, "subject": subject, "ts": ts})
        return tags

    # ── version inspection (read-only, by git ref) ──
    def read_file_at(self, rel_path: str, ref: str) -> str:
        """Contents of ``rel_path`` as of ``ref`` (a commit sha or tag)."""
        self._abs(rel_path)  # validate containment
        return self._git("show", f"{ref}:{rel_path}")

    def diff(self, rel_path: str, ref_a: str, ref_b: str) -> str:
        """Unified diff of ``rel_path`` between two refs (empty string if equal)."""
        self._abs(rel_path)
        return self._git("diff", "--no-color", ref_a, ref_b, "--", rel_path)

    def restore(self, rel_path: str, ref: str, message: str, author: str) -> str:
        """Restore ``rel_path`` to its ``ref`` content as a NEW commit (non-destructive)."""
        content = self.read_file_at(rel_path, ref)
        return self.write_file(rel_path, content, message, author)
