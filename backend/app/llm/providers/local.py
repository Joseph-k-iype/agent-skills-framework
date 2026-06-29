"""Offline provider: deterministic feature-hashing embeddings, no chat.

This makes the whole platform — and its tests — work fully offline with genuine
lexical similarity (shared words → higher cosine). It is the default provider
and the fallback every other provider degrades to when it has no API key.
"""

from __future__ import annotations

import hashlib
import math
import re

from app.core.config import settings
from app.llm.providers.base import EmbedOneMixin

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


class LocalProvider(EmbedOneMixin):
    name = "local"

    def __init__(self) -> None:
        self.dim = settings.embedding_dim

    @property
    def has_chat(self) -> bool:
        return False

    @property
    def using_real_embeddings(self) -> bool:
        return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [local_embedding(t, self.dim) for t in texts]

    async def chat(self, system: str, user: str) -> str | None:
        return None
