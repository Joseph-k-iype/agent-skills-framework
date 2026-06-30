"""EAKSO SDK — fetch a marketplace skill and apply it to your own LLM call.

    from eakso import Client

    client = Client(api_key="sk_live_...")
    skill = client.skill("<listing-id>")
    answer = skill.apply(my_llm, "Summarise this invoice")  # usage auto-reported

``my_llm`` is any callable ``(system_prompt, user_input) -> str`` — bring your own
model/provider. The SDK never executes anything itself; it injects the skill body
as the system prompt and reports an ``apply`` usage event back to EAKSO.
"""

from __future__ import annotations

from typing import Any, Callable

import httpx

DEFAULT_BASE_URL = "http://localhost:8000/api/v1"


def _unwrap(payload: dict) -> dict:
    """Pull ``data`` out of the EAKSO response envelope (or raise on error)."""
    if isinstance(payload, dict) and "data" in payload:
        if payload.get("success") is False:
            err = payload.get("error", {})
            raise EaksoError(err.get("message", "request failed"))
        return payload["data"]
    return payload


class EaksoError(RuntimeError):
    pass


class Skill:
    """A fetched marketplace skill, ready to apply to an LLM call."""

    def __init__(self, client: "Client", data: dict) -> None:
        self._client = client
        self.id: str = data["id"]
        self.title: str = data.get("title", "")
        self.version: str = data.get("version", "")
        self.type: str | None = data.get("type")
        self.content: str = data.get("content", "")
        self.body: str = data.get("body", "")
        self.system_prompt: str = data.get("system_prompt", "")

    def apply(
        self,
        llm: Callable[[str, str], str],
        user_input: str,
        *,
        report: bool = True,
        meta: dict | None = None,
    ) -> str:
        """Run ``llm(system_prompt, user_input)`` with the skill applied; report usage."""
        result = llm(self.system_prompt, user_input)
        if report:
            self._client.report_usage(self.id, kind="apply", meta=meta or {})
        return result

    def __repr__(self) -> str:  # pragma: no cover - cosmetic
        return f"Skill(id={self.id!r}, title={self.title!r}, version={self.version!r})"


class Client:
    """Thin client over the EAKSO SDK endpoints, authenticated by API key."""

    def __init__(
        self,
        api_key: str,
        base_url: str = DEFAULT_BASE_URL,
        *,
        timeout: float = 30.0,
        transport: Any = None,
    ) -> None:
        if not api_key:
            raise EaksoError("api_key is required")
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(
            timeout=timeout,
            headers={"Authorization": f"Bearer {api_key}"},
            transport=transport,
        )

    def skill(self, listing_id: str) -> Skill:
        resp = self._http.get(f"{self.base_url}/sdk/skill/{listing_id}")
        resp.raise_for_status()
        return Skill(self, _unwrap(resp.json()))

    def report_usage(self, listing_id: str, *, kind: str = "apply", meta: dict | None = None) -> None:
        """Best-effort usage report — never raises into the caller's flow."""
        try:
            self._http.post(
                f"{self.base_url}/sdk/usage",
                json={"listing_id": listing_id, "kind": kind, "meta": meta or {}},
            )
        except Exception:
            pass

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: Any) -> None:
        self.close()
