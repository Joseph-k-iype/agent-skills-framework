"""Business-logic wrapper around TaxonomyRepository.

Validates the ``label`` parameter against the controlled vocabulary
``{"Capability", "Source"}`` and raises ``ValueError`` on unknown values
(the router maps this to HTTP 400).
"""

from __future__ import annotations

from app.repositories.taxonomy_repo import TaxonomyRepository

_ALLOWED_LABELS: frozenset[str] = frozenset({"Capability", "Source"})


class TaxonomyService:
    """Thin service that validates labels and delegates to the repo."""

    def __init__(self, graph=None) -> None:  # noqa: ANN001
        self._repo = TaxonomyRepository(graph)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _check_label(label: str) -> str:
        if label not in _ALLOWED_LABELS:
            raise ValueError(
                f"Unknown taxonomy label {label!r}. "
                f"Must be one of {sorted(_ALLOWED_LABELS)}."
            )
        return label

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def tree(self, label: str) -> list[dict]:
        """Return all terms for *label* with parent_key populated."""
        self._check_label(label)
        return await self._repo.list_tree(label)

    async def proposed(self) -> list[dict]:
        """All terms across both labels with status='proposed'."""
        return await self._repo.list_proposed()

    async def create(
        self,
        label: str,
        key: str,
        label_text: str,
        description: str | None = None,
        parent_key: str | None = None,
    ) -> dict:
        """Create or update a term; wire hierarchy if parent_key provided."""
        self._check_label(label)
        return await self._repo.upsert_term(
            label, key, label_text, description, "proposed", parent_key
        )

    async def promote(self, label: str, key: str) -> dict | None:
        """Promote a proposed term to canonical status."""
        self._check_label(label)
        return await self._repo.promote(label, key)

    async def merge(self, label: str, key: str, into_key: str) -> bool:
        """Merge alias *key* into *into_key*, repointing Concept edges."""
        self._check_label(label)
        return await self._repo.merge_term(label, key, into_key)
