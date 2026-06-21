from __future__ import annotations

from pathlib import Path

import pytest

from harness import SkillTestHarness

# The bundled reference skill, used as a real fixture for the harness.
REF_SKILL = Path(__file__).resolve().parents[2] / "skills" / "data-discovery"


@pytest.fixture
def harness():
    return SkillTestHarness(REF_SKILL)


def test_reads_manifest(harness):
    assert harness.manifest["name"] == "data-discovery"


def test_load_skill_returns_baseskill(harness):
    skill = harness.load_skill()
    assert skill.name == "data-discovery"


@pytest.mark.asyncio
async def test_run_command_end_to_end(harness):
    await harness.initialize({"sources": [{"name": "db", "type": "postgresql"}],
                             "catalog_endpoint": "http://x"})
    result = await harness.run_command("/discover")
    assert result.status == "success"
    assert result.data["sources_crawled"] == 1


@pytest.mark.asyncio
async def test_run_command_passes_payload_through(harness):
    await harness.initialize({"sources": [], "catalog_endpoint": ""})
    result = await harness.run_command("/profile", [], {"unused": "value"})
    assert result.status == "success"


@pytest.mark.asyncio
async def test_health(harness):
    await harness.initialize({"sources": [], "catalog_endpoint": ""})
    health = await harness.health()
    assert health.healthy is True


def test_missing_manifest(tmp_path):
    with pytest.raises(FileNotFoundError):
        SkillTestHarness(tmp_path)
