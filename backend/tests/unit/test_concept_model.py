"""Concept model: frontmatter + body + computed links (free-text type/runtime)."""

from __future__ import annotations

from app.okf.concept import parse_concept, to_markdown


def test_parse_basic_skill():
    content = (
        "---\n"
        "type: skill\n"
        "title: Invoice OCR\n"
        "description: Extracts line items\n"
        "runtime: python 3.12\n"
        "tags: [finance, ocr]\n"
        "capabilities: [extraction:invoice]\n"
        "owner: jo\n"
        "---\n"
        "# Body\n\nSee [the validator](../payments/validator.md).\n"
    )
    c = parse_concept("finance/ocr/invoice-ocr.md", content)
    assert c.type == "skill"
    assert c.title == "Invoice OCR"
    assert c.runtime == "python 3.12"  # free text, preserved verbatim
    assert c.tags == ["finance", "ocr"]
    assert c.capabilities == ["extraction:invoice"]
    # unknown frontmatter key preserved
    assert c.frontmatter["owner"] == "jo"
    # relative link resolved to a repo-relative path
    assert c.links == ["finance/payments/validator.md"]


def test_missing_type_defaults_to_document():
    c = parse_concept("notes/x.md", "---\ntitle: X\n---\nbody")
    assert c.type == "document"


def test_runtime_accepts_any_value():
    c = parse_concept("a.md", "---\ntype: agent\nruntime: rust 1.79 + wasm\n---\nbody")
    assert c.runtime == "rust 1.79 + wasm"


def test_to_markdown_round_trips():
    md = to_markdown(
        {"type": "skill", "title": "T", "runtime": "go", "tags": ["x"]},
        "# Hello\n",
    )
    c = parse_concept("a.md", md)
    assert c.type == "skill"
    assert c.title == "T"
    assert c.runtime == "go"
    assert c.tags == ["x"]
    assert c.body.strip() == "# Hello"


def test_links_ignore_external_and_anchors():
    body = "[ext](https://x.com) [anchor](#h) [rel](./y.md)"
    c = parse_concept("dir/a.md", "---\ntype: doc\n---\n" + body)
    assert c.links == ["dir/y.md"]
