from _fake_chat_model import FakeToolCallingChatModel
from langchain_core.messages import AIMessage

from skill_sdk.evaluation import agent_exec
from skill_sdk.evaluation.agent_exec import run_agent
from skill_sdk.evaluation.sandbox import make_workspace

PERMS = [{"resource": "workspace", "actions": ["read", "write", "create", "list"]}]


def test_run_agent_executes_tool_then_finishes():
    ws = make_workspace(PERMS)
    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "write_file", "args": {"path": "out.txt", "content": "hi"}, "id": "1"}]),
        AIMessage(content="done"),
    ])
    res = run_agent("create out.txt", ws, model, skill_body="Always write out.txt.")
    assert res.error is None
    assert (ws.path / "out.txt").read_text() == "hi"
    assert res.final_text == "done"
    assert any(e.name == "write_file" for e in res.trajectory.events)


def test_run_agent_respects_step_cap():
    ws = make_workspace(PERMS)
    # model keeps requesting tools forever; step_cap must stop it
    looping = [AIMessage(content="", tool_calls=[
        {"name": "list_dir", "args": {"path": "."}, "id": str(i)}]) for i in range(50)]
    model = FakeToolCallingChatModel(responses=looping)
    res = run_agent("loop", ws, model, step_cap=3)
    assert res.error is not None
    assert "step cap" in res.error.lower()


def test_run_agent_populates_duration_ms(monkeypatch):
    ws = make_workspace(PERMS)
    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "write_file", "args": {"path": "out.txt", "content": "hi"}, "id": "1"}]),
        AIMessage(content="done"),
    ])
    times = iter([0.0, 0.5])
    monkeypatch.setattr(agent_exec.time, "monotonic", lambda: next(times))
    res = run_agent("create out.txt", ws, model, skill_body="Always write out.txt.")
    assert res.error is None
    assert res.trajectory.duration_ms == 500


def test_run_agent_populates_duration_ms_on_step_cap(monkeypatch):
    ws = make_workspace(PERMS)
    looping = [AIMessage(content="", tool_calls=[
        {"name": "list_dir", "args": {"path": "."}, "id": str(i)}]) for i in range(50)]
    model = FakeToolCallingChatModel(responses=looping)
    times = iter([0.0, 1.25])
    monkeypatch.setattr(agent_exec.time, "monotonic", lambda: next(times))
    res = run_agent("loop", ws, model, step_cap=3)
    assert res.error is not None
    assert res.trajectory.duration_ms == 1250


def test_run_agent_populates_duration_ms_on_exception(monkeypatch):
    ws = make_workspace(PERMS)

    def boom(*args, **kwargs):
        raise RuntimeError("boom")

    model = FakeToolCallingChatModel(responses=[])
    monkeypatch.setattr(model, "bind_tools", boom)
    times = iter([0.0, 0.2])
    monkeypatch.setattr(agent_exec.time, "monotonic", lambda: next(times))
    res = run_agent("create out.txt", ws, model)
    assert res.error is not None
    assert res.trajectory.duration_ms == 200


def test_run_agent_duration_ms_is_non_negative_real_clock():
    ws = make_workspace(PERMS)
    model = FakeToolCallingChatModel(responses=[
        AIMessage(content="", tool_calls=[
            {"name": "write_file", "args": {"path": "out.txt", "content": "hi"}, "id": "1"}]),
        AIMessage(content="done"),
    ])
    res = run_agent("create out.txt", ws, model, skill_body="Always write out.txt.")
    assert isinstance(res.trajectory.duration_ms, int)
    assert res.trajectory.duration_ms >= 0
