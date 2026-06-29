"""OpenRouter provider — OpenAI-compatible embeddings + chat completions.

Lights up only when ``openrouter_api_key`` is set; otherwise embeddings fall
back to the local hash embedding and chat is unavailable.
"""

from __future__ import annotations

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.providers.base import EmbedOneMixin
from app.llm.providers.local import local_embedding

log = get_logger("llm.openrouter")


class OpenRouterProvider(EmbedOneMixin):
    name = "openrouter"

    def __init__(self) -> None:
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.dim = settings.embedding_dim

    @property
    def has_chat(self) -> bool:
        return bool(self.api_key)

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

    async def chat(self, system: str, user: str) -> str | None:
        if not self.api_key:
            return None
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                resp = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json={
                        "model": settings.chat_model,
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user", "content": user},
                        ],
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            log.warning("openrouter_chat_failed", error=str(exc))
            return None
