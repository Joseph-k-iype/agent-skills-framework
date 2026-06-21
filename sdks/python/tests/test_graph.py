import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from skill_sdk.graph import FalkorDBConnector, GRAPH_QUERIES


@pytest.fixture
def connector():
    return FalkorDBConnector(enabled=False)


def test_connector_disabled_by_default(connector):
    assert connector.connected is False


def test_connector_enabled_but_not_connected():
    c = FalkorDBConnector(enabled=True)
    assert c.connected is False


@pytest.mark.asyncio
async def test_connect_fails_gracefully():
    c = FalkorDBConnector(host="nonexistent.local", port=6379, enabled=True)
    result = await c.connect()
    assert result is False
    assert c.connected is False


def test_query_returns_empty_when_not_connected(connector):
    result = connector.query("RETURN 1")
    assert result == []


def test_register_skill_skipped_when_not_connected(connector):
    result = connector.register_skill("/fake/path")
    assert result == {"status": "skipped", "reason": "not connected"}


def test_register_deployment_skipped_when_not_connected(connector):
    result = connector.register_deployment("id", "dep", "test", "dev")
    assert result == {"status": "skipped", "reason": "not connected"}


def test_find_skills_by_capability_empty(connector):
    result = connector.find_skills_by_capability("test:cap")
    assert result == []


def test_find_skills_by_permission_empty(connector):
    result = connector.find_skills_by_permission("test:resource")
    assert result == []


def test_find_impact_empty(connector):
    result = connector.find_impact("some-id")
    assert result == []


def test_graph_queries_present():
    required = [
        "create_skill_node",
        "create_version_node",
        "link_version_to_skill",
        "link_capability",
        "link_dependency",
        "link_permission",
        "register_deployment",
        "find_impact",
        "find_skill_by_capability",
        "find_skill_by_permission",
        "get_dependency_chain",
        "list_deployments",
    ]
    for key in required:
        assert key in GRAPH_QUERIES, f"Missing query: {key}"
        assert GRAPH_QUERIES[key].strip(), f"Empty query: {key}"


def test_connect_retry_no_redis():
    c = FalkorDBConnector(enabled=True)
    with patch.object(c, "connect", return_value=False):
        import asyncio
        result = asyncio.run(c.connect())
        assert result is False


@patch("skill_sdk.graph.load_manifest")
def test_register_skill_integration(mock_load):
    c = FalkorDBConnector(enabled=True)

    mock_load.return_value = {
        "id": f"skill://sha256/{'b' * 64}/test@1.0.0",
        "name": "test",
        "version": "1.0.0",
        "description": "test skill",
        "runtime": "python",
        "entry": "main.py",
        "capabilities": ["test:cap"],
        "dependencies": {"skills": ["other-skill@^1.0.0"]},
        "permissions": [{"resource": "filesystem:workspace", "actions": ["read", "write"]}],
    }

    manifest_path = Path(tempfile.mktemp(suffix=".json"))
    manifest_path.write_text("{}")

    c._graph = MagicMock()
    result = c.register_skill(manifest_path)

    assert result["status"] != "error"
