"""Interactive eval test cases — a versioned suite shipped alongside a skill.

A skill may carry a sibling ``<slug>.eval.yaml`` file in its bundle directory
holding ``{cases: [{input, expected}]}``. Because it lives in the git-backed
bundle it is versioned and travels with the skill (toward the marketplace). Each
case is an ``input`` (what the user sends) and the ``expected`` correct output to
grade the skill's actual output against.
"""

from __future__ import annotations

from pathlib import PurePosixPath

import yaml


def cases_path(concept_path: str) -> str:
    """Sibling eval-cases file for a concept. ``a/b/x.md`` → ``a/b/x.eval.yaml``."""
    p = PurePosixPath(concept_path)
    return str(p.parent / f"{p.stem}.eval.yaml")


def parse_cases(text: str) -> list[dict]:
    """Parse the YAML suite into a normalized ``[{input, expected}]`` list."""
    data = yaml.safe_load(text) or {}
    raw = data.get("cases", []) if isinstance(data, dict) else []
    out: list[dict] = []
    for item in raw if isinstance(raw, list) else []:
        if isinstance(item, dict):
            out.append(
                {
                    "input": str(item.get("input", "")),
                    "expected": str(item.get("expected", "")),
                }
            )
    return out


def dump_cases(cases: list[dict]) -> str:
    """Serialize cases back to the YAML suite (stable key order)."""
    payload = {
        "cases": [
            {"input": str(c.get("input", "")), "expected": str(c.get("expected", ""))}
            for c in cases
        ]
    }
    return yaml.safe_dump(payload, sort_keys=False, allow_unicode=True)
