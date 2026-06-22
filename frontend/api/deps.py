from __future__ import annotations

import os
import threading
from pathlib import Path
from skill_sdk.graph import FalkorDBConnector
from skill_sdk.registry import RegistryClient

GRAPH_HOST_ENV = "SKILLS_GRAPH_HOST"
GRAPH_PORT_ENV = "SKILLS_GRAPH_PORT"

_registry_path = Path(__file__).parent.parent.parent / "registry"
_registry_client: RegistryClient | None = None
_registry_client_lock = threading.Lock()


def get_registry_path() -> Path:
    return _registry_path.resolve()


def get_registry() -> RegistryClient:
    global _registry_client
    if _registry_client is None:
        with _registry_client_lock:
            if _registry_client is None:
                graph = None
                host = os.environ.get(GRAPH_HOST_ENV)
                if host:
                    # A bad SKILLS_GRAPH_PORT must not crash every request that
                    # touches the registry — fall back to the default port.
                    try:
                        port = int(os.environ.get(GRAPH_PORT_ENV, 6379))
                    except (TypeError, ValueError):
                        port = 6379
                    graph = FalkorDBConnector(host=host, port=port, enabled=True)
                client = RegistryClient(get_registry_path(), graph=graph)
                client.auto_tag = False
                _registry_client = client
    return _registry_client
