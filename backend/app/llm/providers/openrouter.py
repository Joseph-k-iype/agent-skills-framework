"""OpenRouter provider — OpenAI-compatible embeddings + chat completions.

Lights up only when ``openrouter_api_key`` is set; otherwise embeddings fall
back to the local hash embedding and chat is unavailable. Transient rate-limits
(429) and upstream hiccups (5xx) are retried with exponential backoff.
"""

from __future__ import annotations

import asyncio

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.providers.base import EmbedOneMixin
from app.llm.providers.local import local_embedding

log = get_logger("llm.openrouter")

_RETRY_STATUS = {429, 500, 502, 503, 504}
_MAX_ATTEMPTS = 4


async def _post_with_retry(url: str, headers: dict, json: dict, timeout: float) -> httpx.Response:
    """POST with exponential backoff on rate-limit / transient upstream errors."""
    last_exc: Exception | None = None
    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(_MAX_ATTEMPTS):
            try:
                resp = await client.post(url, headers=headers, json=json)
                if resp.status_code in _RETRY_STATUS and attempt < _MAX_ATTEMPTS - 1:
                    delay = 2.0**attempt
                    retry_after = resp.headers.get("retry-after")
                    if retry_after and retry_after.isdigit():
                        delay = max(delay, float(retry_after))
                    log.warning("openrouter_retry", status=resp.status_code, delay=delay)
                    await asyncio.sleep(delay)
                    continue
                resp.raise_for_status()
                return resp
            except httpx.HTTPStatusError:
                raise
            except Exception as exc:  # network blip — retry
                last_exc = exc
                if attempt < _MAX_ATTEMPTS - 1:
                    await asyncio.sleep(2.0**attempt)
                    continue
                raise
    if last_exc:
        raise last_exc
    raise RuntimeError("unreachable")


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

    async def embed_checked(self, texts: list[str]) -> tuple[list[list[float]], bool]:
        # No key → genuine offline hash embeddings (real for this provider).
        if not self.api_key:
            return [local_embedding(t, self.dim) for t in texts], True
        try:
            resp = await _post_with_retry(
                f"{self.base_url}/embeddings",
                {"Authorization": f"Bearer {self.api_key}"},
                {"model": settings.embedding_model, "input": texts},
                timeout=60,
            )
            return [item["embedding"] for item in resp.json()["data"]], True
        except Exception as exc:
            # Degraded fallback: keeps ingestion alive, but the caller must NOT
            # persist this as a real embedding (it would poison semantic search).
            log.warning("openrouter_embed_failed_fallback_local", error=str(exc))
            return [local_embedding(t, self.dim) for t in texts], False

    async def embed(self, texts: list[str]) -> list[list[float]]:
        vectors, _ = await self.embed_checked(texts)
        return vectors

    async def chat(self, system: str, user: str) -> str | None:
        if not self.api_key:
            return None
        try:
            resp = await _post_with_retry(
                f"{self.base_url}/chat/completions",
                {"Authorization": f"Bearer {self.api_key}"},
                {
                    "model": settings.chat_model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                },
                timeout=120,
            )
            return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            log.warning("openrouter_chat_failed", error=str(exc))
            return None
