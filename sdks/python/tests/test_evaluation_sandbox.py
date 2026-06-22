import shutil
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


def test_deny_list_is_case_insensitive():
    ws = make_workspace(PERMS_FS)
    with pytest.raises(DestructiveCommandError):
        run_command("RM -RF /", ws.path)


def test_deny_list_blocks_home_and_flag_variants():
    ws = make_workspace(PERMS_FS)
    for cmd in (
        "rm -rf ~",
        "rm -fr /",
        "rm -rf --no-preserve-root /",
        "rm -rf $HOME",
    ):
        with pytest.raises(DestructiveCommandError):
            run_command(cmd, ws.path)


def test_deny_list_allows_safe_rm():
    ws = make_workspace(PERMS_FS)
    # Must not raise; directory need not exist, command may fail at the shell level.
    run_command("rm -rf ./build", ws.path)


PERMS_DELETE = [{"resource": "workspace", "actions": ["delete"]}]


def test_delete_tool_present_when_declared():
    ws = make_workspace(PERMS_DELETE)
    target = ws.path / "doomed.txt"
    target.write_text("bye")
    traj = Trajectory()
    tools = {t.name: t for t in build_tools(ws, traj)}
    assert "delete_file" in tools
    tools["delete_file"].invoke({"path": "doomed.txt"})
    assert not target.exists()
    assert any(e.name == "delete_file" for e in traj.events)


def test_delete_tool_absent_when_not_declared():
    ws = make_workspace(PERMS_FS)  # no "delete"
    tools = {t.name: t for t in build_tools(ws, Trajectory())}
    assert "delete_file" not in tools


def test_safe_join_rejects_sibling_prefix_escape():
    ws = make_workspace(PERMS_FS)
    # Construct a sibling directory that shares ws.path's basename as a
    # *prefix* (e.g. ws.path="/tmp/skill-eval-abc", sibling="/tmp/skill-eval-abc-evil").
    # The old check `str(target).startswith(str(ws.resolve()))` would have
    # allowed this because the sibling's path string literally starts with
    # the workspace's path string. The fixed boundary check must reject it.
    sibling = ws.path.parent / (ws.path.name + "-evil")
    sibling.mkdir()
    (sibling / "x.txt").write_text("secret")
    try:
        rel = f"../{sibling.name}/x.txt"
        traj = Trajectory()
        tools = {t.name: t for t in build_tools(ws, traj)}

        read_out = tools["read_file"].invoke({"path": rel})
        assert "error" in read_out
        assert "escapes workspace" in read_out

        write_out = tools["write_file"].invoke({"path": rel, "content": "pwned"})
        assert "error" in write_out
        assert "escapes workspace" in write_out
        assert (sibling / "x.txt").read_text() == "secret"  # untouched
    finally:
        shutil.rmtree(sibling, ignore_errors=True)
