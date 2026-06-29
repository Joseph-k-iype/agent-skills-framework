"""Redesign settings: configurable workspaces root + pluggable LLM provider."""

from __future__ import annotations

from app.core.config import settings


def test_workspaces_root_defaults_to_a_workspaces_dir():
    assert settings.workspaces_root
    assert settings.workspaces_root.replace("\\", "/").rstrip("/").endswith("workspaces")


def test_llm_provider_defaults_to_local():
    assert settings.llm_provider == "local"


def test_provider_keys_present_and_default_empty():
    assert settings.anthropic_api_key == ""
    assert settings.openai_api_key == ""
