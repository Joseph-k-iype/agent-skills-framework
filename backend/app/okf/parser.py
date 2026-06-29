"""Link extraction for OKF markdown bodies.

OKF concepts link to each other with ordinary markdown links (and we also accept
``[[wikilinks]]``). Those links are the graph edges; :func:`extract_links`
returns their raw targets, which :mod:`app.okf.concept` then resolves to
repo-relative paths.
"""

from __future__ import annotations

import re

_WIKILINK = re.compile(r"\[\[([^\]]+?)\]\]")
_MDLINK = re.compile(r"\[[^\]]*\]\(([^)]+?)\)")


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
