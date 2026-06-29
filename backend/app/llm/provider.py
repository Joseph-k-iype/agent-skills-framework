"""Pluggable LLM provider abstraction.

The active provider is chosen by ``settings.llm_provider``. Every provider
exposes the same surface — ``embed`` (always works, falling back to local hash
embeddings) and ``chat`` (returns ``None`` when no real chat is available). This
lets embeddings and the eval agents run fully offline, and lights up real models
purely by configuration. Nothing here hardcodes a single vendor.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from app.core.config import settings
from app.llm.providers.anthropic import AnthropicProvider
from app.llm.providers.local import LocalProvider
from app.llm.providers.openai_provider import OpenAIProvider
from app.llm.providers.openrouter import OpenRouterProvider


@runtime_checkable
class LLMProvider(Protocol):
    name: str

    @property
    def has_chat(self) -> bool: ...

    @property
    def using_real_embeddings(self) -> bool: ...

    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_one(self, text: str) -> list[float]: ...

    async def chat(self, system: str, user: str) -> str | None: ...


_REGISTRY = {
    "local": LocalProvider,
    "openrouter": OpenRouterProvider,
    "anthropic": AnthropicProvider,
    "openai": OpenAIProvider,
}


def _auto_select() -> str:
    """Pick a provider from whichever key is configured, else offline local."""
    if settings.openrouter_api_key:
        return "openrouter"
    if settings.anthropic_api_key:
        return "anthropic"
    if settings.openai_api_key:
        return "openai"
    return "local"


def get_provider() -> LLMProvider:
    """Return the configured provider.

    ``auto`` (the default) detects a provider from configured keys; an explicit
    name is honored as-is; anything unknown falls back to local.
    """
    name = settings.llm_provider
    if name == "auto":
        name = _auto_select()
    cls = _REGISTRY.get(name, LocalProvider)
    return cls()
