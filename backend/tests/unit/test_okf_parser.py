"""Pure unit tests for OKF link extraction (used to build graph edges)."""

from __future__ import annotations

from app.okf.parser import extract_links


def test_external_links_are_ignored():
    links = extract_links("[a](https://x.com) [b](./local.md) [c](#anchor)")
    assert links == ["./local.md"]


def test_wikilinks_and_md_links_are_extracted():
    body = "Links to [[Doc B]] and [glossary](glossary.md) and [ext](https://example.com)."
    links = extract_links(body)
    assert "Doc B" in links
    assert "glossary.md" in links
    assert all(not link.startswith("http") for link in links)
