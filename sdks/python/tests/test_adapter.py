import json
import tempfile
from pathlib import Path

import pytest
import yaml

from skill_sdk.adapter import generate_markdown_integration, generate_skill_doc

VALID_HASH = "a" * 64


@pytest.fixture
def minimal_manifest():
    return {
        "name": "test-skill",
        "version": "1.0.0",
        "description": "A test skill",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
        "triggers": {
            "events": ["data.updated"],
            "commands": ["/run"],
        },
        "capabilities": ["test:execute"],
        "config": {
            "required": ["api_key"],
        },
        "dependencies": {
            "pip": ["requests>=2.0"],
            "npm": [],
            "skills": ["other@^1.0.0"],
        },
        "permissions": [
            {"resource": "api", "actions": ["read", "write"]},
        ],
        "id": f"skill://sha256/{VALID_HASH}/test-skill@1.0.0",
    }


@pytest.fixture
def manifest_path(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    path = tmp / "skill.yaml"
    path.write_text(yaml.dump(minimal_manifest))
    (tmp / "src").mkdir()
    (tmp / "src" / "main.py").write_text("# placeholder")
    return path


def test_generate_markdown_includes_name(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert "# test-skill v1.0.0" in md


def test_generate_markdown_includes_id(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert f"skill://sha256/{VALID_HASH}/test-skill@1.0.0" in md


def test_generate_markdown_includes_triggers(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert "data.updated" in md
    assert "/run" in md


def test_generate_markdown_includes_capabilities(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert "test:execute" in md


def test_generate_markdown_includes_config(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert "api_key" in md


def test_generate_markdown_includes_deps(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert "requests>=2.0" in md
    assert "other@^1.0.0" in md


def test_generate_markdown_includes_permissions(manifest_path):
    md = generate_markdown_integration(manifest_path)
    assert "api" in md
    assert "read" in md


def test_generate_markdown_writes_to_file(manifest_path):
    output = tempfile.mktemp(suffix=".md")
    md = generate_markdown_integration(manifest_path, output)
    assert Path(output).read_text() == md
    assert len(md) > 0


def test_generate_json_format(manifest_path):
    result = generate_skill_doc(manifest_path, format="json")
    data = json.loads(result)
    assert data["name"] == "test-skill"
    assert data["version"] == "1.0.0"
    assert data["runtime"] == "python"


def test_invalid_format(manifest_path):
    with pytest.raises(ValueError, match="Unsupported format"):
        generate_skill_doc(manifest_path, format="html")


def test_missing_manifest():
    with pytest.raises(Exception):
        generate_markdown_integration("/nonexistent/skill.yaml")
