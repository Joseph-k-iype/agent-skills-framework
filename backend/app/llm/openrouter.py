"""Back-compat shim for the old OpenRouter-only LLM gateway.

The LLM layer is now provider-pluggable (see ``app.llm.provider``). This module
keeps the historical import surface (``get_llm``, ``local_embedding``,
``OpenRouterClient``) working so existing callers don't break.
"""

from __future__ import annotations

from app.llm.provider import LLMProvider, get_provider
from app.llm.providers.local import local_embedding
from app.llm.providers.openrouter import OpenRouterProvider

# Historical name kept as an alias.
OpenRouterClient = OpenRouterProvider


def get_llm() -> LLMProvider:
    """Return the configured LLM provider (was OpenRouter-only)."""
    return get_provider()


__all__ = ["get_llm", "local_embedding", "OpenRouterClient", "LLMProvider"]
