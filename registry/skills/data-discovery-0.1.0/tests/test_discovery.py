import importlib.util
from pathlib import Path

import pytest

from skill_sdk import SkillContext, SkillCommand, compute_skill_id


@pytest.fixture(scope="session")
def skill_cls():
    src_path = Path(__file__).parent.parent / "src" / "main.py"
    spec = importlib.util.spec_from_file_location("skill_main", src_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.Skill


@pytest.fixture
def skill(skill_cls):
    return skill_cls()


@pytest.fixture
def context():
    return SkillContext(
        config={
            "sources": [
                {
                    "name": "test_db",
                    "type": "postgresql",
                    "connection_string": "postgresql://localhost/test",
                }
            ],
            "catalog_endpoint": "http://localhost:8080/api/catalog",
        },
        state={"skill_id": "skill://sha256/test/data-discovery@0.1.0"},
    )


@pytest.mark.asyncio
async def test_initialize(skill, context):
    await skill.initialize(context)
    assert len(skill.sources) == 1
    assert skill.catalog_endpoint == "http://localhost:8080/api/catalog"
    assert skill.skill_id == "skill://sha256/test/data-discovery@0.1.0"


@pytest.mark.asyncio
async def test_discover_command(skill, context):
    await skill.initialize(context)
    result = await skill.handle_command(SkillCommand(name="/discover"))
    assert result.status == "success"
    assert result.data["sources_crawled"] == 1
    assert result.data["assets_discovered"] >= 1


@pytest.mark.asyncio
async def test_profile_command(skill, context):
    await skill.initialize(context)
    result = await skill.handle_command(SkillCommand(name="/profile"))
    assert result.status == "success"
    assert result.data["sources_profiled"] == 1


@pytest.mark.asyncio
async def test_unknown_command(skill, context):
    await skill.initialize(context)
    result = await skill.handle_command(SkillCommand(name="/nonexistent"))
    assert result.status == "error"


@pytest.mark.asyncio
async def test_health_check(skill, context):
    await skill.initialize(context)
    health = await skill.health_check()
    assert health.healthy is True
    assert health.version == "0.1.0"
    assert health.details["sources_configured"] == 1


@pytest.mark.asyncio
async def test_event_handler(skill, context):
    await skill.initialize(context)
    from skill_sdk import SkillEvent
    result = await skill.handle_event(SkillEvent(
        name="data.source.connected",
        payload={"source": {"name": "new_source", "type": "mysql"}},
    ))
    assert result.status == "success"
