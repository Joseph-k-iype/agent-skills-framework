"""The six evaluators: known-bad concepts produce findings; clean ones score high."""

from __future__ import annotations

from app.evals.cost import CostEvaluator
from app.evals.documentation import DocumentationEvaluator
from app.evals.governance import GovernanceEvaluator
from app.evals.performance import PerformanceEvaluator
from app.evals.quality import QualityEvaluator
from app.evals.security import SecurityEvaluator
from app.okf.concept import parse_concept

CLEAN = parse_concept(
    "finance/invoice-ocr.md",
    "---\ntype: skill\ntitle: Invoice OCR\ndescription: Extracts line items\n"
    "tags: [finance]\n---\n# Overview\n\nUses OCR.\n\n```python\nx = 1\n```\n",
)


def test_security_flags_secret_and_blocks():
    bad = parse_concept(
        "a.md",
        "---\ntype: skill\n---\nAWS_SECRET_ACCESS_KEY=AKIAIOSFODNN7EXAMPLE\n",
    )
    r = SecurityEvaluator().run_rules(bad, [])
    assert r.blocking is True
    assert any(f.severity == "error" for f in r.findings)
    assert SecurityEvaluator().run_rules(CLEAN, []).blocking is False


def test_documentation_flags_broken_link():
    bad = parse_concept("dir/a.md", "---\ntype: doc\ndescription: x\n---\n[v](missing.md)")
    r = DocumentationEvaluator().run_rules(bad, ["dir/a.md"])
    assert any("Broken internal link" in f.message for f in r.findings)


def test_documentation_flags_empty_mermaid():
    bad = parse_concept("a.md", "---\ntype: doc\ndescription: x\n---\n```mermaid\n```\n")
    r = DocumentationEvaluator().run_rules(bad, ["a.md"])
    assert any("mermaid" in f.message.lower() for f in r.findings)


def test_governance_flags_missing_type():
    bad = parse_concept("a.md", "---\ntitle: X\n---\nbody")  # no type in frontmatter
    r = GovernanceEvaluator().run_rules(bad, [])
    assert r.blocking is True
    assert any("type" in f.message for f in r.findings)


def test_governance_clean_scores_well():
    r = GovernanceEvaluator().run_rules(CLEAN, [])
    assert r.blocking is False
    assert r.score >= 90.0


def test_cost_is_informational_and_nonblocking():
    r = CostEvaluator().run_rules(CLEAN, [])
    assert r.blocking is False
    assert any("token" in f.message.lower() for f in r.findings)


def test_cost_warns_on_huge_body():
    big = parse_concept("a.md", "---\ntype: doc\n---\n" + ("word " * 5000))
    r = CostEvaluator().run_rules(big, [])
    assert r.score < 100.0


def test_performance_warns_on_long_body():
    big = parse_concept("a.md", "---\ntype: doc\n---\n" + ("line\n" * 500))
    r = PerformanceEvaluator().run_rules(big, [])
    assert any("long" in f.message.lower() for f in r.findings)


def test_quality_thin_body_scores_lower_than_clean():
    thin = parse_concept("a.md", "---\ntype: doc\n---\nhi")
    thin_score = QualityEvaluator().run_rules(thin, []).score
    clean_score = QualityEvaluator().run_rules(CLEAN, []).score
    assert clean_score > thin_score
