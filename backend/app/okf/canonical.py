"""Deterministic content-addressing for skills.

The SHA is computed over a canonical serialization so that semantically
identical content (key order, line endings, trailing whitespace) yields the
same hash. Used as the immutable, content-addressed identity of a published
skill version.
"""

from __future__ import annotations

import hashlib
import json


def _normalize_body(body: str) -> str:
    lines = body.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    stripped = [ln.rstrip() for ln in lines]
    text = "\n".join(stripped).strip("\n")
    return text + "\n" if text else ""


def canonical_bytes(frontmatter: dict, body: str) -> bytes:
    fm = json.dumps(
        frontmatter or {},
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    )
    return (fm + "\n" + _normalize_body(body)).encode("utf-8")


def content_sha(frontmatter: dict, body: str) -> str:
    return hashlib.sha256(canonical_bytes(frontmatter, body)).hexdigest()


def short_sha(sha: str) -> str:
    return sha[:7]
