from skill_sdk.evaluation.state import EvaluationReport, ExecutorSummary


def test_report_to_dict_shape():
    report = EvaluationReport(
        skill_name="demo",
        skill_version="1.0.0",
        run_at="2026-01-01T00:00:00+00:00",
        judge_status="skipped",
        judge_skip_reason="no model configured",
        structural_errors=[],
        structural_warnings=["No 'tests/' directory found (recommended)"],
        content_critic_findings=[],
        test_executor=ExecutorSummary(total=2, passed=1, failed=1, results=[{"case_id": "a"}]),
        overall_score=None,
        summary="ok",
    )
    d = report.to_dict()
    assert d["skill_name"] == "demo"
    assert d["judge_status"] == "skipped"
    assert d["content_critic"] == {"findings": [], "model": None}
    assert d["test_executor"] == {
        "results": [{"case_id": "a"}],
        "passed": 1,
        "failed": 1,
        "total": 2,
    }
    assert d["overall_score"] is None


def test_overall_score_defaults_to_none_not_zero():
    report = EvaluationReport(
        skill_name="demo",
        skill_version="1.0.0",
        run_at="2026-01-01T00:00:00+00:00",
        judge_status="skipped",
        judge_skip_reason=None,
    )
    assert report.overall_score is None
    assert report.to_dict()["overall_score"] is None
