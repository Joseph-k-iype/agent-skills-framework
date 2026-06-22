from skill_sdk.evaluation.state import (
    AgentExecutionSummary,
    ConfigAggregate,
    EvaluationReport,
    ExecutorSummary,
    compute_overall_score,
)


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


def _report():
    return EvaluationReport(skill_name="s", skill_version="1.0.0", run_at="t",
                            judge_status="ok", judge_skip_reason=None)


def test_report_to_dict_has_agent_execution_none_by_default():
    assert _report().to_dict()["agent_execution"] is None


def test_compute_overall_score_judge_ok_no_findings_includes_full_content_score():
    # judge ran (status "ok") and the content critic found nothing — the
    # content component must still count, at full marks (100), averaged with
    # the test-executor component. Non-boundary pass rate (3/4 = 75, not
    # 0/100) so a regression to "gate on findings non-empty" is caught:
    # that bug would silently drop the content component and yield 75.0
    # instead of the correct 87.5.
    report = EvaluationReport(
        skill_name="s", skill_version="1.0.0", run_at="t",
        judge_status="ok", judge_skip_reason=None,
        test_executor=ExecutorSummary(passed=3, failed=1, total=4),
        content_critic_findings=[],
    )
    assert compute_overall_score(report) == 87.5


def test_compute_overall_score_judge_skipped_excludes_content_component():
    # judge did not run (status "skipped") — the content critic never ran,
    # so it must not contribute any score, even though findings is empty.
    report = EvaluationReport(
        skill_name="s", skill_version="1.0.0", run_at="t",
        judge_status="skipped", judge_skip_reason="no model configured",
        test_executor=ExecutorSummary(passed=3, failed=1, total=4),
        content_critic_findings=[],
    )
    assert compute_overall_score(report) == 75.0


def test_compute_overall_score_judge_ok_no_findings_with_agent_execution():
    # All three components present: test_executor (75), content (100, judge
    # ran clean), agent_execution (50, non-boundary). Mean of [75, 100, 50].
    report = EvaluationReport(
        skill_name="s", skill_version="1.0.0", run_at="t",
        judge_status="ok", judge_skip_reason=None,
        test_executor=ExecutorSummary(passed=3, failed=1, total=4),
        content_critic_findings=[],
        agent_execution=AgentExecutionSummary(
            comparison_mode="with_without",
            skip_reason=None,
            runs_per_case=3,
            with_skill=ConfigAggregate(pass_rate_mean=0.5),
            baseline=ConfigAggregate(pass_rate_mean=0.1),
        ),
    )
    assert compute_overall_score(report) == 75.0


def test_agent_execution_summary_serializes():
    summ = AgentExecutionSummary(
        comparison_mode="with_without", skip_reason=None, runs_per_case=1,
        with_skill=ConfigAggregate(pass_rate_mean=1.0),
        baseline=ConfigAggregate(pass_rate_mean=0.0),
        delta={"pass_rate": 1.0, "tokens": 50.0, "duration": 10.0}, cases=[])
    r = _report()
    r.agent_execution = summ
    d = r.to_dict()["agent_execution"]
    assert d["comparison_mode"] == "with_without"
    assert d["with_skill"]["pass_rate_mean"] == 1.0
    assert d["delta"]["pass_rate"] == 1.0
