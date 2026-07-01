"""Taxonomy read endpoints — capabilities and sources trees."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.deps import CurrentUser, require_permission
from app.schemas.taxonomy import TaxonomyTreeOut, TermOut
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
