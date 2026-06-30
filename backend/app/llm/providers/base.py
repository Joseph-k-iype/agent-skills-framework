"""Shared provider behavior."""

from __future__ import annotations


class EmbedOneMixin:
    """Convenience ``embed_one`` defined in terms of ``embed``."""

    async def embed(self, texts: list[str]) -> list[list[float]]:  # pragma: no cover
        raise NotImplementedError

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]

    async def embed_checked(self, texts: list[str]) -> tuple[list[list[float]], bool]:
        """Return ``(vectors, is_real)``.

        ``is_real`` is ``False`` only when the vectors are a degraded *error*
        fallback (e.g. the remote embedding API was rate-limited and we substituted
        the local hash). It is NOT about neural-vs-lexical: a provider's own
        genuine embedding — including the offline local hash — counts as real, so
        offline mode stays searchable. The default assumes the provider's own
        ``embed`` is genuine; only providers that fall back on error override this.
        """
        return await self.embed(texts), True

    async def embed_one_checked(self, text: str) -> tuple[list[float], bool]:
        vectors, is_real = await self.embed_checked([text])
        return vectors[0], is_real
