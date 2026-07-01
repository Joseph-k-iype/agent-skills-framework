"""The OKF Concept — one markdown file in a workspace bundle.

A concept is YAML frontmatter (only ``type`` is required; everything else is
optional and unknown keys are preserved) plus a markdown body. Markdown links in
the body are the graph edges; we resolve relative links to repo-relative paths
so the indexer can connect them. ``type`` and ``runtime`` are free text — there
is no fixed taxonomy, per the OKF spec.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePosixPath

import frontmatter

from app.okf.parser import extract_links


@dataclass
class Concept:
    path: str  # repo-relative, e.g. "finance/payments/invoice-ocr.md"
    type: str
    title: str
    description: str | None = None
    runtime: str | None = None
    tags: list[str] = field(default_factory=list)
    capabilities: list[str] = field(default_factory=list)
    sources: list[str] = field(default_factory=list)
    frontmatter: dict = field(default_factory=dict)
    body: str = ""
    links: list[str] = field(default_factory=list)

    def embedding_text(self) -> str:
        tagline = " ".join(self.tags)
        return f"{self.title}\n{self.description or ''}\n{tagline}\n{self.body}".strip()


def _as_list(value: object) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [v.strip() for v in value.split(",") if v.strip()]
    if isinstance(value, (list, tuple)):
        return [str(v) for v in value]
    return [str(value)]


def _resolve_link(file_path: str, target: str) -> str | None:
    """Resolve a body link target to a repo-relative path, or None to drop it."""
    if target.startswith(("http://", "https://", "#", "mailto:")):
        return None
    base_dir = PurePosixPath(file_path).parent
    # Only resolve things that look like file paths; bare wikilink titles that
    # are not .md paths are dropped by the caller.
    candidate = (base_dir / target).as_posix() if not target.startswith("/") else target.lstrip("/")
    # Normalize ".." segments.
    parts: list[str] = []
    for seg in candidate.split("/"):
        if seg in ("", "."):
            continue
        if seg == "..":
            if parts:
                parts.pop()
            continue
        parts.append(seg)
    return "/".join(parts)


def parse_concept(rel_path: str, content: str) -> Concept:
    post = frontmatter.loads(content)
    meta = dict(post.metadata or {})
    body = post.content or ""

    stem = PurePosixPath(rel_path).stem
    ctype = str(meta.get("type") or "document")
    title = str(meta.get("title") or stem.replace("-", " ").title())
    description = meta.get("description")
    runtime = meta.get("runtime")

    raw_links = extract_links(body)
    links: list[str] = []
    for target in raw_links:
        resolved = _resolve_link(rel_path, target)
        if resolved and resolved.endswith(".md") and resolved not in links:
            links.append(resolved)

    return Concept(
        path=rel_path,
        type=ctype,
        title=title,
        description=str(description) if description is not None else None,
        runtime=str(runtime) if runtime is not None else None,
        tags=_as_list(meta.get("tags")),
        capabilities=_as_list(meta.get("capabilities")),
        sources=_as_list(meta.get("sources")),
        frontmatter=meta,
        body=body,
        links=links,
    )


def to_markdown(fields: dict, body: str) -> str:
    """Serialize frontmatter ``fields`` + ``body`` back to an OKF markdown file."""
    post = frontmatter.Post(body, **{k: v for k, v in fields.items() if v is not None})
    return frontmatter.dumps(post)
