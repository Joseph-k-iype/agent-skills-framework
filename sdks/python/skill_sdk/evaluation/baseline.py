from __future__ import annotations

import json
import statistics
from pathlib import Path
from typing import Any

from ..validation import find_manifest_file, load_manifest
from .agent_exec import run_agent
from .assertions import evaluate_assertions
from .sandbox import cleanup, make_workspace
from .state import AgentExecutionSummary, ConfigAggregate
from .trajectory import RunResult


def _skill_body(skill_path: Path) -> str:
    """The Markdown body of SKILL.md (instructions the agent must follow)."""
    mp = find_manifest_file(skill_path)
    if mp is None or mp.name != "SKILL.md":
        return ""
    text = mp.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) == 3:
            return parts[2].strip()
    return text


def find_previous_version(registry_path: Path, name: str, current_version: str) -> Path | None:
    from ..versioning import is_semver

    skills_dir = Path(registry_path) / "skills"
    if not skills_dir.exists():
        return None
    candidates: list[tuple[tuple[int, ...], Path]] = []
    for d in skills_dir.iterdir():
        if not d.is_dir() or not d.name.startswith(f"{name}-"):
            continue
        ver = d.name[len(name) + 1 :]
        if not is_semver(ver):
            continue
        key = tuple(int(x) for x in ver.split("+")[0].split("-")[0].split("."))
        cur = tuple(int(x) for x in current_version.split("+")[0].split("-")[0].split("."))
        if key < cur:
            candidates.append((key, d))
    if not candidates:
        return None
    return max(candidates, key=lambda c: c[0])[1]


def _workspace_summary(result: RunResult) -> str:
    ws = Path(result.workspace_path) if result.workspace_path else None
    files = []
    if ws and ws.exists():
        for p in sorted(ws.rglob("*")):
            if p.is_file() and "node_modules" not in p.parts:
                files.append(str(p.relative_to(ws)))
    cmds = [e.name for e in result.trajectory.commands()]
    return f"files={files[:40]}\ncommands={cmds[:40]}\nfinal_text={result.final_text[:1000]}"


def judge_run(model, case: dict[str, Any], result: RunResult) -> dict[str, Any]:
    llm_asserts = [
        a for a in case.get("expect", {}).get("assertions", []) if a.get("kind") == "llm"
    ]
    rubric = case.get("expect", {}).get("rubric")
    if not llm_asserts and not rubric:
        return {}
    statements = [a.get("statement", "") for a in llm_asserts]
    prompt = (
        "Grade this agent run. Respond ONLY with JSON: "
        '{"llm_assertions":[{"statement":str,"passed":bool,"evidence":str}],'
        '"rubric_score":int|null}.\n'
        f"Statements to grade: {json.dumps(statements)}\n"
        f"Holistic rubric (0-100, null if none): {json.dumps(rubric)}\n\n"
        f"Run summary:\n{_workspace_summary(result)}"
    )
    try:
        from langchain_core.messages import HumanMessage

        ai = model.invoke([HumanMessage(prompt)])
        text = ai.content if isinstance(ai.content, str) else str(ai.content)
        start, end = text.find("{"), text.rfind("}")
        return json.loads(text[start : end + 1]) if start != -1 else {}
    except Exception:
        return {}


def _aggregate(
    per_run_pass: list[float], tokens: list[int], durations: list[int]
) -> ConfigAggregate:
    def _ms(xs):  # mean+stddev helper
        return (
            statistics.fmean(xs) if xs else 0.0,
            statistics.pstdev(xs) if len(xs) > 1 else 0.0,
        )

    pr_m, pr_s = _ms(per_run_pass)
    tk_m, tk_s = _ms(tokens)
    du_m, du_s = _ms(durations)
    return ConfigAggregate(
        pass_rate_mean=pr_m,
        pass_rate_stddev=pr_s,
        tokens_mean=tk_m,
        tokens_stddev=tk_s,
        duration_mean=du_m,
        duration_stddev=du_s,
    )


def _run_one(skill_path, body, permissions, case, model, *, full_surface, keep):
    ws = make_workspace(
        permissions, files=case.get("input", {}).get("files"), skill_path=skill_path
    )
    try:
        res = run_agent(
            case["input"]["prompt"],
            ws,
            model,
            skill_body=None if full_surface else body,
            full_surface=full_surface,
        )
        typed = evaluate_assertions(case, res, input_files=ws.input_files)
        judged = judge_run(model, case, res)
        llm_results = judged.get("llm_assertions", [])
        all_results = typed + [
            {"kind": "llm", "passed": bool(r.get("passed")), "evidence": r.get("evidence", "")}
            for r in llm_results
        ]
        # permission violation forces this run to 0
        if res.permission_violations:
            pass_rate = 0.0
        elif all_results:
            pass_rate = sum(1 for r in all_results if r["passed"]) / len(all_results)
        else:
            pass_rate = 0.0
        return {
            "pass_rate": pass_rate,
            "tokens": res.trajectory.tokens_in + res.trajectory.tokens_out,
            "duration": res.trajectory.duration_ms,
            "assertions": all_results,
            "rubric_score": judged.get("rubric_score"),
            "violations": res.permission_violations,
            "error": res.error,
        }
    finally:
        cleanup(ws, keep=keep)


def run_agent_execution(
    skill_path: Path,
    manifest: dict[str, Any],
    registry_path: Path,
    task_cases: list[dict[str, Any]],
    model,
    *,
    default_runs: int = 1,
    keep_artifacts: bool = False,
) -> AgentExecutionSummary:
    permissions = manifest.get("permissions", [])
    body = _skill_body(skill_path)
    name = manifest.get("name", skill_path.name)
    version = manifest.get("version", "0.0.0")

    prev = find_previous_version(registry_path, name, version)
    mode = "vs_previous" if prev else "with_without"
    prev_body = _skill_body(prev) if prev else ""
    prev_perms = []
    if prev:
        mp = find_manifest_file(prev)
        if mp:
            try:
                prev_perms = load_manifest(mp).get("permissions", [])
            except Exception:
                prev_perms = []

    runs_per_case = max((c.get("runs", default_runs) for c in task_cases), default=default_runs)
    with_pass, with_tok, with_dur = [], [], []
    base_pass, base_tok, base_dur = [], [], []
    case_reports = []

    for case in task_cases:
        n = case.get("runs", default_runs)
        cw, cb = [], []
        for _ in range(n):
            w = _run_one(
                skill_path, body, permissions, case, model, full_surface=False, keep=keep_artifacts
            )
            with_pass.append(w["pass_rate"])
            with_tok.append(w["tokens"])
            with_dur.append(w["duration"])
            cw.append(w)
            if mode == "vs_previous":
                b = _run_one(
                    prev,
                    prev_body,
                    prev_perms,
                    case,
                    model,
                    full_surface=False,
                    keep=keep_artifacts,
                )
            else:
                b = _run_one(
                    skill_path, "", permissions, case, model, full_surface=True, keep=keep_artifacts
                )
            base_pass.append(b["pass_rate"])
            base_tok.append(b["tokens"])
            base_dur.append(b["duration"])
            cb.append(b)
        case_reports.append({"case_id": case["id"], "with_skill": cw, "baseline": cb})

    with_agg = _aggregate(with_pass, with_tok, with_dur)
    base_agg = _aggregate(base_pass, base_tok, base_dur)
    delta = {
        "pass_rate": round(with_agg.pass_rate_mean - base_agg.pass_rate_mean, 4),
        "tokens": round(with_agg.tokens_mean - base_agg.tokens_mean, 1),
        "duration": round(with_agg.duration_mean - base_agg.duration_mean, 1),
    }
    return AgentExecutionSummary(
        comparison_mode=mode,
        skip_reason=None,
        runs_per_case=runs_per_case,
        with_skill=with_agg,
        baseline=base_agg,
        delta=delta,
        cases=case_reports,
    )
