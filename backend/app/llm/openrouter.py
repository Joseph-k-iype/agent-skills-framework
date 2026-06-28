"""OpenRouter gateway for embeddings (and chat, used by later phases).

When ``OPENROUTER_API_KEY`` is set, real embeddings are requested. Otherwise a
deterministic local *feature-hashing* embedding is used so the platform — and
its tests — work fully offline with genuine lexical similarity (shared words →
higher cosine). Swap in a key for true semantic search; the dimension is fixed
by ``settings.embedding_dim`` either way.
"""

from __future__ import annotations

import hashlib
import math
import re

import httpx

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("llm")

_TOKEN = re.compile(r"[a-z0-9]+")


def _hash_bucket(token: str, dim: int) -> tuple[int, float]:
    h = hashlib.md5(token.encode()).digest()
    bucket = int.from_bytes(h[:4], "big") % dim
    sign = 1.0 if h[4] & 1 else -1.0
    return bucket, sign


def local_embedding(text: str, dim: int) -> list[float]:
    """Deterministic feature-hashing embedding with L2 normalization."""
    vec = [0.0] * dim
    for tok in _TOKEN.findall(text.lower()):
        bucket, sign = _hash_bucket(tok, dim)
        vec[bucket] += sign
    norm = math.sqrt(sum(v * v for v in vec))
    if norm > 0:
        vec = [v / norm for v in vec]
    return vec


class OpenRouterClient:
    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.dim = settings.embedding_dim

    @property
    def using_real_embeddings(self) -> bool:
        return bool(self.api_key)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        if not self.api_key:
            return [local_embedding(t, self.dim) for t in texts]
        try:
            async with httpx.AsyncClient(timeout=60) as client:
                resp = await client.post(
                    f"{self.base_url}/embeddings",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={"model": settings.embedding_model, "input": texts},
                )
                resp.raise_for_status()
                data = resp.json()["data"]
                return [item["embedding"] for item in data]
        except Exception as exc:  # graceful fallback keeps ingestion working
            log.warning("openrouter_embed_failed_fallback_local", error=str(exc))
            return [local_embedding(t, self.dim) for t in texts]

    async def embed_one(self, text: str) -> list[float]:
        return (await self.embed([text]))[0]


def get_llm() -> OpenRouterClient:
    return OpenRouterClient()
