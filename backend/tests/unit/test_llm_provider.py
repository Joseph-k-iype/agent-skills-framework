"""Pluggable LLM provider abstraction."""

from __future__ import annotations

import pytest

from app.core.config import settings
from app.llm.provider import get_provider


@pytest.mark.asyncio
async def test_local_provider_embeds_and_has_no_chat(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "local", raising=False)
    p = get_provider()
    assert p.name == "local"
    assert p.has_chat is False
    assert p.using_real_embeddings is False
    vecs = await p.embed(["hello world", "another"])
    assert len(vecs) == 2
    assert len(vecs[0]) == settings.embedding_dim
    assert await p.chat("sys", "user") is None


@pytest.mark.asyncio
async def test_openrouter_without_key_falls_back_to_local_embeddings(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "openrouter", raising=False)
    monkeypatch.setattr(settings, "openrouter_api_key", "", raising=False)
    p = get_provider()
    assert p.name == "openrouter"
    assert p.using_real_embeddings is False
    vecs = await p.embed(["x"])
    assert len(vecs[0]) == settings.embedding_dim
    # no key -> no chat capability
    assert p.has_chat is False
    assert await p.chat("s", "u") is None


def test_get_llm_alias_still_works():
    from app.llm.openrouter import get_llm

    assert get_llm() is not None


def test_unknown_provider_falls_back_to_local(monkeypatch):
    monkeypatch.setattr(settings, "llm_provider", "does-not-exist", raising=False)
    p = get_provider()
    assert p.name == "local"
