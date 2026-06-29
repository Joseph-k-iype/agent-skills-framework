"""Anthropic provider — chat via the Messages API.

Anthropic has no embeddings endpoint, so embeddings use the local hash
embedding; chat lights up when ``anthropic_api_key`` is set.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.providers.base import EmbedOneMixin
from app.llm.providers.local import local_embedding

log = get_logger("llm.anthropic")

_API = "https://api.anthropic.com/v1/messages"


class AnthropicProvider(EmbedOneMixin):
    name = "anthropic"

    def __init__(self) -> None:
        self.api_key = settings.anthropic_api_key
        self.dim = settings.embedding_dim
        # chat_model may be an OpenRouter-style id; strip a leading vendor prefix.
        self.model = settings.chat_model.split("/")[-1]

    @property
    def has_chat(self) -> bool:
        return bool(self.api_key)

    @property
    def using_real_embeddings(self) -> bool:
        return False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [local_embedding(t, self.dim) for t in texts]

    async def chat(self, system: str, user: str) -> str | None:
        if not self.api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    _API,
                    headers={
                        "x-api-key": self.api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "max_tokens": 1024,
                        "system": system,
                        "messages": [{"role": "user", "content": user}],
                    },
                )
                resp.raise_for_status()
                blocks = resp.json().get("content", [])
                return "".join(b.get("text", "") for b in blocks) or None
        except Exception as exc:
            log.warning("anthropic_chat_failed", error=str(exc))
            return None
