"""Pure unit tests for OKF parsing + link resolution."""

from __future__ import annotations

from app.okf.linker import resolve_links
from app.okf.parser import extract_links, parse_document

DOC_A = """---
id: doc-a
title: Doc A
type: policy
tags: [finance, revenue]
---

Body links to [[Doc B]] and [glossary](glossary.md) and an
external [site](https://example.com) which must be ignored.
"""

DOC_B = """---
id: doc-b
title: Doc B
type: runbook
---

References [[Doc A]] and a [missing](nope.md) link.
"""


def test_parse_extracts_frontmatter_and_links():
    doc = parse_document("doc-a.md", DOC_A)
    assert doc.id == "doc-a"
    assert doc.title == "Doc A"
    assert doc.type == "policy"
    assert doc.tags == ["finance", "revenue"]
    assert "Doc B" in doc.raw_links
    assert "glossary.md" in doc.raw_links


def test_external_links_are_ignored():
    links = extract_links("[a](https://x.com) [b](./local.md) [c](#anchor)")
    assert links == ["./local.md"]


def test_id_falls_back_to_filename_slug():
    doc = parse_document("My File.md", "no frontmatter here")
    assert doc.id == "my-file"
    assert doc.title == "My File"


def test_resolve_links_and_orphans():
    a = parse_document("doc-a.md", DOC_A)
    glossary = parse_document("glossary.md", "---\nid: glossary\ntitle: Glossary\n---\nterms")
    b = parse_document("doc-b.md", DOC_B)
    orphans = resolve_links([a, glossary, b])

    assert set(a.references) == {"doc-b", "glossary"}
    assert b.references == ["doc-a"]
    assert "nope.md" in orphans
