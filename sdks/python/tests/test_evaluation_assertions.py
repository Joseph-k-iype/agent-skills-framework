import tempfile
from pathlib import Path

from skill_sdk.evaluation.assertions import evaluate_assertions
from skill_sdk.evaluation.trajectory import RunResult, Trajectory, TrajectoryEvent


def _ws_with(files: dict[str, str]) -> str:
    ws = Path(tempfile.mkdtemp())
    for rel, content in files.items():
        p = ws / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content)
    return str(ws)


def test_file_exists_glob_pass_and_fail():
    ws = _ws_with({"src/App.tsx": "x", "package.json": "{}"})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "file_exists", "path": "src/*.tsx"},
        {"kind": "file_exists", "path": "missing.txt"},
    ]}}
    out = evaluate_assertions(case, res)
    assert out[0]["passed"] is True
    assert out[1]["passed"] is False


def test_file_contains_text():
    ws = _ws_with({"src/index.css": '@import "tailwindcss";'})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "file_contains", "path": "src/index.css", "text": '@import "tailwindcss"'},
    ]}}
    assert evaluate_assertions(case, res)[0]["passed"] is True


def test_command_ran_substring_and_regex():
    traj = Trajectory()
    traj.add(TrajectoryEvent(kind="command", name="npm install --silent", exit_code=0))
    res = RunResult(trajectory=traj)
    case = {"expect": {"assertions": [
        {"kind": "command_ran", "pattern": "npm install"},
        {"kind": "command_ran", "pattern": "/npm (install|ci)/"},
        {"kind": "command_ran", "pattern": "yarn add"},
    ]}}
    out = evaluate_assertions(case, res)
    assert [o["passed"] for o in out] == [True, True, False]


def test_exit_code_matches_named_command():
    traj = Trajectory()
    traj.add(TrajectoryEvent(kind="command", name="npm run build", exit_code=0))
    res = RunResult(trajectory=traj)
    case = {
        "expect": {"assertions": [{"kind": "exit_code", "command": "npm run build", "equals": 0}]}
    }
    assert evaluate_assertions(case, res)[0]["passed"] is True


def test_no_extra_files_respects_allowlist_and_inputs():
    ws = _ws_with({"package.json": "{}", "node_modules/x.js": "x", "stray.tmp": "junk",
                   "data.csv": "given"})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "no_extra_files", "allow": ["package.json", "node_modules/**"]},
    ]}}
    out = evaluate_assertions(case, res, input_files=["data.csv"])
    assert out[0]["passed"] is False
    assert "stray.tmp" in out[0]["evidence"]


def test_llm_assertions_are_skipped_here():
    res = RunResult()
    case = {"expect": {"assertions": [{"kind": "llm", "statement": "looks good"}]}}
    assert evaluate_assertions(case, res) == []


def test_no_extra_files_rejects_stray_sharing_only_basename():
    # data.csv is the legitimate input, at a nested-ish relative path. A stray file at the
    # workspace root happens to share that basename. The old code allowed *any* file whose
    # basename matched an input file's basename (`Path(f).name for f in input_files`), so a
    # stray "data.csv" at the root would have been allowed even though the real input is
    # "inputs/data.csv" -- a false pass. input_files entries are exact workspace-relative
    # names, so basename-matching is both redundant and wrong.
    ws = _ws_with({"inputs/data.csv": "given", "data.csv": "unrelated stray"})
    res = RunResult(workspace_path=ws)
    case = {"expect": {"assertions": [
        {"kind": "no_extra_files", "allow": []},
    ]}}
    out = evaluate_assertions(case, res, input_files=["inputs/data.csv"])
    assert out[0]["passed"] is False
    assert "data.csv" in out[0]["evidence"]


def test_exit_code_without_equals_fails():
    traj = Trajectory()
    traj.add(TrajectoryEvent(kind="command", name="npm run build", exit_code=None))
    res = RunResult(trajectory=traj)
    case = {
        "expect": {"assertions": [{"kind": "exit_code", "command": "npm run build"}]}
    }
    assert evaluate_assertions(case, res)[0]["passed"] is False
