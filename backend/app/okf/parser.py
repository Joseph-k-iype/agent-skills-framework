"""Parse OKF markdown documents (YAML frontmatter + body + links).

Pure and dependency-light so it is fast to unit test. OKF convention: a markdown
file with YAML frontmatter (id, title, type, tags) and a body that links to other
documents via ``[[wikilinks]]`` or ``[text](relative/path.md)``.
"""

from __future__ import annotations

import re
from pathlib import PurePosixPath

import frontmatter

_WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
_MDLINK = re.compile(r"\[[^\]]*\]\(([^)]+?)\)")


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def extract_links(body: str) -> list[str]:
    """Return raw link targets: wikilink titles and relative markdown paths."""
    links: list[str] = []
    links.extend(m.group(1).strip() for m in _WIKILINK.finditer(body))
    for m in _MDLINK.finditer(body):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        links.append(target)
    return links


def parse_document(relative_path: str, content: str):
    """Parse one OKF file into an OkfDocument. ``id`` falls back to a path slug."""
    from app.okf.models import OkfDocument

    post = frontmatter.loads(content)
    meta = dict(post.metadata or {})
    body = post.content or ""

    stem = PurePosixPath(relative_path).stem
    doc_id = str(meta.get("id") or _slug(stem))
    title = str(meta.get("title") or stem.replace("-", " ").title())
    doc_type = str(meta.get("type") or "document")
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [t.strip() for t in tags.split(",") if t.strip()]

    return OkfDocument(
        id=doc_id,
        title=title,
        type=doc_type,
        relative_path=relative_path,
        body=body,
        tags=[str(t) for t in tags],
        metadata=meta,
        raw_links=extract_links(body),
    )
