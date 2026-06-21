from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from skill_sdk.evaluation import evaluate_skill
from skill_sdk.evaluation.cases import load_eval_cases, save_eval_cases, validate_eval_cases
from skill_sdk.evaluation.memory import load_feedback, record_feedback
from skill_sdk.registry import RegistryClient
from skill_sdk.validation import ValidationError

from .. import audit
from ..deps import get_registry, get_registry_path
from ..security import require_api_key

router = APIRouter()

# Sibling of registry/skills/_feedback/ — NOT inside registry/skills/<name>-<version>/,
# since that directory's file set is exactly what compute_skill_id/validate_skill_id
# hash; writing a report there after publish would corrupt the skill's recorded id.
EVAL_REPORTS_DIRNAME = "_eval_reports"


class UpdateCasesRequest(BaseModel):
    cases: list[dict[str, Any]]


class RunEvaluationRequest(BaseModel):
    judge: str | None = None


class FeedbackRequest(BaseModel):
    finding_id: str
    finding_signature: str
    finding_text: str
    verdict: str
    run_id: str | None = None
    verdict_by: str | None = None


def _skill_dir_or_404(name: str, registry: RegistryClient) -> Path:
    try:
        info = registry.info(name)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    rel_path = info.get("locations", {}).get("local")
    if not rel_path:
        raise HTTPException(status_code=404, detail="Skill files not found locally")
    return get_registry_path() / rel_path


def _eval_report_path(registry_path: Path, name: str, version: str) -> Path:
    return registry_path / "skills" / EVAL_REPORTS_DIRNAME / f"{name}-{version}.json"


def read_eval_report(registry_path: Path, name: str, version: str) -> dict[str, Any] | None:
    path = _eval_report_path(registry_path, name, version)
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def _write_eval_report(registry_path: Path, name: str, version: str, report: dict[str, Any]) -> None:
    path = _eval_report_path(registry_path, name, version)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, indent=2), encoding="utf-8")


@router.get("/{name}/evaluation/cases")
def get_evaluation_cases(name: str, registry: RegistryClient = Depends(get_registry)):
    skill_dir = _skill_dir_or_404(name, registry)
    try:
        cases = load_eval_cases(skill_dir)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"cases": cases}


@router.put("/{name}/evaluation/cases", dependencies=[Depends(require_api_key)])
def update_evaluation_cases(
    name: str, req: UpdateCasesRequest, registry: RegistryClient = Depends(get_registry)
):
    skill_dir = _skill_dir_or_404(name, registry)
    errors = validate_eval_cases(req.cases)
    if errors:
        raise HTTPException(status_code=400, detail="; ".join(errors))
    save_eval_cases(skill_dir, req.cases)
    audit.record("Eval Cases Updated", name, details=f"{len(req.cases)} case(s)")
    return {"success": True, "cases": req.cases}


@router.post("/{name}/evaluation/run", dependencies=[Depends(require_api_key)])
async def run_evaluation(
    name: str, req: RunEvaluationRequest = RunEvaluationRequest(), registry: RegistryClient = Depends(get_registry)
):
    skill_dir = _skill_dir_or_404(name, registry)
    registry_path = get_registry_path()

    report = await run_in_threadpool(
        evaluate_skill, skill_dir, judge=req.judge, registry_path=registry_path
    )
    report_dict = report.to_dict()
    _write_eval_report(registry_path, report.skill_name, report.skill_version, report_dict)
    audit.record(
        "Skill Evaluated", report.skill_name, report.skill_version,
        details=f"judge={report.judge_status}; score={report.overall_score}",
    )
    return report_dict


@router.get("/{name}/evaluation/latest")
def get_latest_evaluation(
    name: str, version: str | None = None, registry: RegistryClient = Depends(get_registry)
):
    try:
        info = registry.info(name)
    except ValidationError as e:
        raise HTTPException(status_code=404, detail=str(e))
    resolved_version = version or info.get("latest")
    if not resolved_version:
        raise HTTPException(status_code=404, detail="No evaluation report found")
    report = read_eval_report(get_registry_path(), name, resolved_version)
    if report is None:
        raise HTTPException(status_code=404, detail="No evaluation report found")
    return report


@router.get("/{name}/evaluation/feedback")
def get_evaluation_feedback(name: str):
    return load_feedback(get_registry_path(), name)


@router.post("/{name}/evaluation/feedback", dependencies=[Depends(require_api_key)])
def submit_evaluation_feedback(name: str, req: FeedbackRequest):
    if req.verdict not in ("accepted", "dismissed"):
        raise HTTPException(status_code=400, detail="verdict must be 'accepted' or 'dismissed'")
    entry = record_feedback(
        get_registry_path(),
        name,
        finding_id=req.finding_id,
        finding_signature=req.finding_signature,
        finding_text=req.finding_text,
        verdict=req.verdict,
        run_id=req.run_id,
        verdict_by=req.verdict_by,
    )
    audit.record("Eval Finding " + req.verdict.capitalize(), name, details=req.finding_text)
    return {"success": True, "entry": entry}
