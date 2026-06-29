"""Shared provider behavior."""

from __future__ import annotations


class EmbedOneMixin:
    """Convenience ``embed_one`` defined in terms of ``embed``."""

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]
