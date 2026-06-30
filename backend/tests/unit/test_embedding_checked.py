"""Provider embed_checked — distinguishes a real embedding from a degraded fallback."""

from __future__ import annotations

import pytest

from app.llm.providers.local import LocalProvider
from app.llm.providers.openrouter import OpenRouterProvider


@pytest.mark.asyncio
async def test_local_provider_is_always_real():
    vec, is_real = await LocalProvider().embed_one_checked("hello world")
    assert is_real is True  # genuine offline embedding, not an error-fallback
    assert len(vec) > 0


@pytest.mark.asyncio
async def test_openrouter_success_is_real(monkeypatch):
    p = OpenRouterProvider()
    monkeypatch.setattr(p, "api_key", "sk-test", raising=False)

    class _Resp:
        @staticmethod
        def json():
            return {"data": [{"embedding": [0.1, 0.2, 0.3]}]}

    async def _ok(*a, **k):
        return _Resp()

    monkeypatch.setattr("app.llm.providers.openrouter._post_with_retry", _ok)
    vecs, is_real = await p.embed_checked(["hi"])
    assert is_real is True
    assert vecs == [[0.1, 0.2, 0.3]]


@pytest.mark.asyncio
async def test_openrouter_failure_falls_back_and_flags_unreal(monkeypatch):
    p = OpenRouterProvider()
    monkeypatch.setattr(p, "api_key", "sk-test", raising=False)

    async def _boom(*a, **k):
        raise RuntimeError("429 rate limited")

    monkeypatch.setattr("app.llm.providers.openrouter._post_with_retry", _boom)
    vecs, is_real = await p.embed_checked(["hi"])
    assert is_real is False  # degraded — caller must NOT persist as real
    assert len(vecs) == 1 and len(vecs[0]) == p.dim  # still a usable vector
