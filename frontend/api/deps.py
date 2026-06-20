from __future__ import annotations

from pathlib import Path
from skill_sdk.registry import RegistryClient

_registry_path = Path(__file__).parent.parent.parent / "registry"
_registry_client: RegistryClient | None = None


def get_registry_path() -> Path:
    return _registry_path.resolve()


def get_registry() -> RegistryClient:
    global _registry_client
    if _registry_client is None:
        _registry_client = RegistryClient(get_registry_path())
        _registry_client.auto_tag = False
    return _registry_client
