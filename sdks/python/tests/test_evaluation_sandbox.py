import tempfile
from pathlib import Path

import pytest

from skill_sdk.evaluation.sandbox import (
    DestructiveCommandError,
    actions_for,
    build_tools,
    make_workspace,
    run_command,
)
from skill_sdk.evaluation.trajectory import Trajectory

PERMS_FS = [{"resource": "workspace", "actions": ["read", "write", "create", "list"]}]
PERMS_NONE = []


def test_actions_for_unions():
    perms = [
        {"resource": "a", "actions": ["read"]},
        {"resource": "b", "actions": ["write", "read"]},
    ]
    assert actions_for(perms) == {"read", "write"}


def test_make_workspace_copies_input_files():
    skill = Path(tempfile.mkdtemp())
    (skill / "tests").mkdir()
    (skill / "tests" / "data.csv").write_text("a,b")
    ws = make_workspace(PERMS_FS, files=["tests/data.csv"], skill_path=skill)
    assert (ws.path / "data.csv").read_text() == "a,b"


def test_write_tool_present_when_declared_records_event():
    ws = make_workspace(PERMS_FS)
    traj = Trajectory()
    tools = {t.name: t for t in build_tools(ws, traj)}
    assert "write_file" in tools
    tools["write_file"].invoke({"path": "out.txt", "content": "hi"})
    assert (ws.path / "out.txt").read_text() == "hi"
    assert any(e.name == "write_file" for e in traj.events)


def test_execute_tool_absent_when_not_declared():
    ws = make_workspace(PERMS_FS)  # no "execute"
    tools = {t.name: t for t in build_tools(ws, Trajectory())}
    assert "run_command" not in tools


def test_full_surface_grants_everything_for_baseline():
    ws = make_workspace(PERMS_NONE)
    tools = {t.name: t for t in build_tools(ws, Trajectory(), full_surface=True)}
    assert "run_command" in tools
    assert "write_file" in tools


def test_run_command_blocks_destructive():
    ws = make_workspace(PERMS_FS)
    with pytest.raises(DestructiveCommandError):
        run_command("rm -rf /", ws.path)


def test_run_command_runs_in_workspace():
    ws = make_workspace(PERMS_FS)
    code, out = run_command("echo hello > note.txt", ws.path)
    assert code == 0
    assert (ws.path / "note.txt").read_text().strip() == "hello"
