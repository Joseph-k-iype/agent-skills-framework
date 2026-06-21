from skill_sdk.evaluation.trajectory import RunResult, Trajectory, TrajectoryEvent


def test_commands_filters_command_events():
    t = Trajectory()
    t.add(TrajectoryEvent(kind="tool", name="read_file"))
    t.add(TrajectoryEvent(kind="command", name="npm install", exit_code=0))
    cmds = t.commands()
    assert len(cmds) == 1
    assert cmds[0].name == "npm install"


def test_trajectory_to_dict_roundtrips_counts():
    t = Trajectory(tokens_in=10, tokens_out=5, duration_ms=1200)
    t.add(TrajectoryEvent(kind="command", name="ls", output="a\nb", exit_code=0))
    d = t.to_dict()
    assert d["tokens_in"] == 10
    assert d["tokens_out"] == 5
    assert d["duration_ms"] == 1200
    assert d["events"][0]["name"] == "ls"


def test_runresult_to_dict_includes_trajectory_and_violations():
    r = RunResult(final_text="done", workspace_path="/tmp/x",
                  permission_violations=["execute not declared"])
    d = r.to_dict()
    assert d["final_text"] == "done"
    assert d["permission_violations"] == ["execute not declared"]
    assert "trajectory" in d
