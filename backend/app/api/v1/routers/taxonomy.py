"""Taxonomy read + curation endpoints."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import CurrentUser, require_permission
from app.schemas.taxonomy import MergeRequest, TermCreate, TaxonomyTreeOut, TermOut
from app.services.taxonomy_service import TaxonomyService

router = APIRouter()

_TERM_DEFAULTS = {"description": None, "parent_key": None}


def _normalise(t: dict) -> dict:
    """Ensure optional fields are present even when FalkorDB omits null props."""
    return {**_TERM_DEFAULTS, **t}


@router.get("/capabilities", response_model=TaxonomyTreeOut)
async def get_capabilities(
    _user: CurrentUser = Depends(require_permission("skill:read")),
) -> TaxonomyTreeOut:
    """Return the flat Capability taxonomy tree (client builds hierarchy)."""
    terms = await TaxonomyService().tree("Capability")
    return TaxonomyTreeOut(terms=[TermOut(**_normalise(t)) for t in terms])


@router.get("/sources", response_model=TaxonomyTreeOut)
async def get_sources(
    _user: CurrentUser = Depends(require_permission("skill:read")),
) -> TaxonomyTreeOut:
    """Return the flat Source taxonomy tree (client builds hierarchy)."""
    terms = await TaxonomyService().tree("Source")
    return TaxonomyTreeOut(terms=[TermOut(**_normalise(t)) for t in terms])


# ---------------------------------------------------------------------------
# Curation endpoints — require taxonomy:manage (admin only)
# ---------------------------------------------------------------------------


@router.get("/proposed", response_model=TaxonomyTreeOut)
async def list_proposed(
    _user: CurrentUser = Depends(require_permission("taxonomy:manage")),
) -> TaxonomyTreeOut:
    """List all proposed terms across Capability and Source labels."""
    terms = await TaxonomyService().proposed()
    return TaxonomyTreeOut(terms=[TermOut(**_normalise(t)) for t in terms])


@router.post("/{label}", response_model=TermOut)
async def create_term(
    label: str,
    body: TermCreate,
    _user: CurrentUser = Depends(require_permission("taxonomy:manage")),
) -> TermOut:
    """Create a canonical term under *label* (Capability or Source)."""
    try:
        term = await TaxonomyService().create(
            label=label,
            key=body.key,
            label_text=body.label,
            description=body.description,
            parent_key=body.parent_key,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return TermOut(**_normalise(term))


@router.post("/{label}/{key}/promote", response_model=TermOut)
async def promote_term(
    label: str,
    key: str,
    _user: CurrentUser = Depends(require_permission("taxonomy:manage")),
) -> TermOut:
    """Promote a proposed term to canonical status."""
    try:
        term = await TaxonomyService().promote(label=label, key=key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if term is None:
        raise HTTPException(status_code=404, detail=f"Term {key!r} not found under {label!r}")
    return TermOut(**_normalise(term))


@router.post("/{label}/{key}/merge")
async def merge_term(
    label: str,
    key: str,
    body: MergeRequest,
    _user: CurrentUser = Depends(require_permission("taxonomy:manage")),
) -> dict:
    """Merge alias *key* into *into_key*, repointing all Concept edges."""
    try:
        ok = await TaxonomyService().merge(label=label, key=key, into_key=body.into_key)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not ok:
        raise HTTPException(
            status_code=400,
            detail=f"Merge target {body.into_key!r} not found under {label!r}",
        )
    return {"ok": True}
