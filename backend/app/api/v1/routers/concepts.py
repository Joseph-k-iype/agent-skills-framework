"""Concepts router — OKF markdown files (skills/agents/prompts/docs).

A concept is addressed by ``workspace_id`` + repo-relative ``path`` (passed as a
query parameter so paths with slashes are unambiguous). Reuses the ``skill:*``
permission codes — a skill is just a concept with ``type: skill``.
"""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser, get_db, require_permission
from app.core.envelope import success
from app.schemas.concept import (
    ConceptCreate,
    ConceptMove,
    ConceptPublish,
    ConceptUpdate,
    EvalCasesBody,
)
from app.services.concept_service import ConceptService
from app.services.index_service import IndexService

router = APIRouter()


async def _heal_embeddings(workspace_id: str) -> None:
    """Background re-embed of any pending nodes (off the request path)."""
    await IndexService().embed_pending(workspace_id)


@router.get("/concepts")
async def list_concepts(
    workspace_id: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    items = ConceptService(db, user).list_concepts(workspace_id)
    return success([c.model_dump() for c in items])


@router.post("/concepts")
async def create_concept(
    workspace_id: str,
    body: ConceptCreate,
    background: BackgroundTasks,
    user: CurrentUser = Depends(require_permission("skill:create")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).create(
        workspace_id=workspace_id,
        folder_path=body.folder_path,
        name=body.name,
        type=body.type,
        description=body.description,
        runtime=body.runtime,
        tags=body.tags,
        capabilities=body.capabilities,
        sources=body.sources,
        body=body.body,
        frontmatter=body.frontmatter,
        parent_path=body.parent_path,
    )
    background.add_task(_heal_embeddings, workspace_id)
    return success(out.model_dump())


@router.get("/concept")
async def get_concept(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).get(workspace_id, path).model_dump())


@router.put("/concept")
async def update_concept(
    workspace_id: str,
    path: str,
    body: ConceptUpdate,
    background: BackgroundTasks,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).update(
        workspace_id=workspace_id,
        path=path,
        title=body.title,
        type=body.type,
        description=body.description,
        runtime=body.runtime,
        tags=body.tags,
        capabilities=body.capabilities,
        sources=body.sources,
        body=body.body,
        frontmatter=body.frontmatter,
        parent_path=body.parent_path,
    )
    background.add_task(_heal_embeddings, workspace_id)
    return success(out.model_dump())


@router.delete("/concept")
async def delete_concept(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:delete")),
    db: AsyncSession = Depends(get_db),
):
    await ConceptService(db, user).delete(workspace_id=workspace_id, path=path)
    return success({"deleted": path})


@router.post("/concept/move")
async def move_concept(
    workspace_id: str,
    path: str,
    body: ConceptMove,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).move(
        workspace_id=workspace_id, src_path=path, dst_folder_path=body.dst_folder_path
    )
    return success(out.model_dump())


@router.get("/concept/history")
async def concept_history(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    items = ConceptService(db, user).history(workspace_id, path)
    return success([v.model_dump() for v in items])


@router.get("/concept/versions")
async def concept_versions(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).versions(workspace_id, path))


@router.get("/concept/version")
async def concept_version_content(
    workspace_id: str,
    path: str,
    ref: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).version_content(workspace_id, path, ref))


@router.get("/concept/diff")
async def concept_diff(
    workspace_id: str,
    path: str,
    a: str,
    b: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).diff_versions(workspace_id, path, a, b))


@router.post("/concept/restore")
async def concept_restore(
    workspace_id: str,
    path: str,
    ref: str,
    background: BackgroundTasks,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).restore_version(workspace_id, path, ref)
    background.add_task(_heal_embeddings, workspace_id)
    return success(out.model_dump())


@router.post("/concept/publish")
async def publish_concept(
    workspace_id: str,
    path: str,
    body: ConceptPublish,
    user: CurrentUser = Depends(require_permission("skill:publish")),
    db: AsyncSession = Depends(get_db),
):
    out = await ConceptService(db, user).publish(
        workspace_id=workspace_id, path=path, version=body.version
    )
    return success(out.model_dump())


@router.post("/concept/evaluate")
async def evaluate_concept(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:evaluate")),
    db: AsyncSession = Depends(get_db),
):
    report = await ConceptService(db, user).evaluate(workspace_id, path)
    return success(report)


@router.post("/concept/deep-evaluate")
async def deep_evaluate_concept(
    workspace_id: str,
    path: str,
    n: int = 5,
    user: CurrentUser = Depends(require_permission("skill:evaluate")),
    db: AsyncSession = Depends(get_db),
):
    report = await ConceptService(db, user).deep_evaluate(workspace_id, path, n_cases=n)
    return success(report)


@router.get("/concept/eval-cases")
async def get_eval_cases(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).get_eval_cases(workspace_id, path))


@router.put("/concept/eval-cases")
async def save_eval_cases(
    workspace_id: str,
    path: str,
    body: EvalCasesBody,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    cases = [c.model_dump() for c in body.cases]
    return success(ConceptService(db, user).save_eval_cases(workspace_id, path, cases))


@router.post("/concept/suggest-eval-cases")
async def suggest_eval_cases(
    workspace_id: str,
    path: str,
    n: int = 5,
    user: CurrentUser = Depends(require_permission("skill:evaluate")),
    db: AsyncSession = Depends(get_db),
):
    cases = await ConceptService(db, user).suggest_eval_cases(workspace_id, path, n=n)
    return success(cases)


@router.post("/concept/grade-eval")
async def grade_eval(
    workspace_id: str,
    path: str,
    body: EvalCasesBody,
    user: CurrentUser = Depends(require_permission("skill:evaluate")),
    db: AsyncSession = Depends(get_db),
):
    cases = [c.model_dump() for c in body.cases]
    report = await ConceptService(db, user).grade_eval(workspace_id, path, cases)
    return success(report)


@router.post("/reindex")
async def reindex_workspace(
    workspace_id: str,
    user: CurrentUser = Depends(require_permission("skill:update")),
    db: AsyncSession = Depends(get_db),
):
    """Rebuild the graph projection from files and heal degraded embeddings."""
    return success(await ConceptService(db, user).reindex(workspace_id))


@router.get("/graph")
async def workspace_graph(
    workspace_id: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    return success(ConceptService(db, user).graph(workspace_id))


@router.get("/concept/graph")
async def concept_neighborhood(
    workspace_id: str,
    path: str,
    user: CurrentUser = Depends(require_permission("skill:read")),
    db: AsyncSession = Depends(get_db),
):
    data = ConceptService(db, user).neighborhood(workspace_id, path)
    return success(data or {"node": None, "edges": []})


@router.get("/search")
async def search_workspace(
    workspace_id: str,
    q: str,
    k: int = 10,
    user: CurrentUser = Depends(require_permission("search:read")),
    db: AsyncSession = Depends(get_db),
):
    results = await ConceptService(db, user).search(workspace_id, q, k)
    return success(results)
