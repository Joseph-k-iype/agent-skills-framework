"""SDK client — fetch + apply + auto usage report, over a mocked transport."""

from __future__ import annotations

import httpx
import pytest

from eakso import Client, EaksoError


def _make_client(handler):
    return Client("sk_live_test", base_url="http://api/api/v1", transport=httpx.MockTransport(handler))


def test_fetch_skill_unwraps_envelope():
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["authorization"] == "Bearer sk_live_test"
        assert request.url.path == "/api/v1/sdk/skill/abc"
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "id": "abc",
                    "title": "Lineage",
                    "version": "1.0.0",
                    "type": "skill",
                    "content": "# Lineage\nbody",
                    "body": "# Lineage\nbody",
                    "system_prompt": "# Skill: Lineage\nbody",
                },
                "errors": [],
            },
        )

    skill = _make_client(handler).skill("abc")
    assert skill.id == "abc" and skill.title == "Lineage"
    assert "# Skill: Lineage" in skill.system_prompt


def test_apply_calls_llm_and_reports_usage():
    seen = {"usage": None}

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sdk/usage"):
            import json

            seen["usage"] = json.loads(request.content)
            return httpx.Response(200, json={"success": True, "data": {"ok": True}, "errors": []})
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {
                    "id": "abc",
                    "title": "Lineage",
                    "version": "1.0.0",
                    "content": "x",
                    "body": "x",
                    "system_prompt": "SYS",
                },
                "errors": [],
            },
        )

    skill = _make_client(handler).skill("abc")
    captured = {}

    def my_llm(system: str, user: str) -> str:
        captured["system"], captured["user"] = system, user
        return "ANSWER"

    out = skill.apply(my_llm, "do the thing")
    assert out == "ANSWER"
    assert captured == {"system": "SYS", "user": "do the thing"}
    assert seen["usage"] == {"listing_id": "abc", "kind": "apply", "meta": {}}


def test_usage_report_is_best_effort():
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/sdk/usage"):
            raise httpx.ConnectError("down")
        return httpx.Response(
            200,
            json={
                "success": True,
                "data": {"id": "abc", "system_prompt": "SYS"},
                "errors": [],
            },
        )

    skill = _make_client(handler).skill("abc")
    # A failing usage report must not raise into the caller.
    assert skill.apply(lambda s, u: "ok", "x") == "ok"


def test_missing_api_key_raises():
    with pytest.raises(EaksoError):
        Client("")
