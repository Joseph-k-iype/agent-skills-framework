"""Resolve raw OKF links to document ids; report unresolved (orphan) links."""

from __future__ import annotations

from pathlib import PurePosixPath

from app.okf.models import OkfDocument


def _slug(value: str) -> str:
    import re

    return re.sub(r"[^a-z0-9]+", "-", value.strip().lower()).strip("-")


def resolve_links(docs: list[OkfDocument]) -> list[str]:
    """Populate ``doc.references`` for each document; return unique orphan targets.

    A raw link resolves if it matches another document's id, title slug, or
    relative path (with or without a .md suffix).
    """
    by_id = {d.id: d for d in docs}
    by_title = {_slug(d.title): d for d in docs}
    by_path: dict[str, OkfDocument] = {}
    for d in docs:
        p = d.relative_path
        by_path[p] = d
        by_path[p.removesuffix(".md")] = d
        by_path[PurePosixPath(p).name] = d
        by_path[PurePosixPath(p).stem] = d

    orphans: set[str] = set()
    for d in docs:
        refs: list[str] = []
        for raw in d.raw_links:
            target = _resolve_one(raw, d, by_id, by_title, by_path)
            if target and target != d.id and target not in refs:
                refs.append(target)
            elif target is None:
                orphans.add(raw)
        d.references = refs
    return sorted(orphans)


def _resolve_one(raw, doc, by_id, by_title, by_path):
    candidates = [raw, raw.removesuffix(".md"), _slug(raw)]
    # markdown relative path resolved against the doc's directory
    parent = PurePosixPath(doc.relative_path).parent
    joined = str(parent / raw).lstrip("./")
    candidates += [joined, joined.removesuffix(".md"), PurePosixPath(raw).stem]
    for c in candidates:
        if c in by_id:
            return by_id[c].id
        if c in by_path:
            return by_path[c].id
        if c in by_title:
            return by_title[c].id
    return None
