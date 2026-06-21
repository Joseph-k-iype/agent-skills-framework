from skill_sdk.context import SkillCommand, SkillEvent


def test_skill_command_payload_defaults_empty_and_is_independent_per_instance():
    a = SkillCommand(name="/x")
    b = SkillCommand(name="/y")
    assert a.payload == {}
    a.payload["k"] = "v"
    assert b.payload == {}


def test_skill_command_accepts_structured_payload():
    cmd = SkillCommand(name="/enrich", payload={"assets": [{"id": "a1"}]})
    assert cmd.payload["assets"] == [{"id": "a1"}]


def test_skill_event_payload_unaffected_by_command_change():
    event = SkillEvent(name="asset.discovered")
    assert event.payload == {}
