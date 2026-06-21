from __future__ import annotations

import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

from .trajectory import Trajectory, TrajectoryEvent

DESTRUCTIVE_PATTERNS = [
    # rm with both -r and -f (any flag order, combined or separate) targeting a
    # dangerous root: /, ~, or $HOME — but NOT ordinary relative paths like ./build.
    r"\brm\b(?:\s+-[a-zA-Z-]+|\s+--[a-z-]+)*\s+"
    r"(?=(?:-[a-zA-Z]*r[a-zA-Z]*\b.*-[a-zA-Z]*f[a-zA-Z]*\b|"
    r"-[a-zA-Z]*f[a-zA-Z]*\b.*-[a-zA-Z]*r[a-zA-Z]*\b|"
    r"-[a-zA-Z]*r[a-zA-Z]*f[a-zA-Z]*\b|-[a-zA-Z]*f[a-zA-Z]*r[a-zA-Z]*\b))"
    r"(?:-[a-zA-Z]+\s+|--[a-z-]+\s+)*(/|~|\$HOME)(\s|$)",
    r":\(\)\s*\{\s*:\|:&\s*\};:",  # fork bomb
    r"\bcurl\b[^|]*\|\s*(sh|bash)\b",  # curl | sh
    r"\bwget\b[^|]*\|\s*(sh|bash)\b",
    r"\bmkfs\b",
    r"\bdd\s+if=",
    r">\s*/dev/sd",
]


class DestructiveCommandError(Exception):
    pass


@dataclass
class Workspace:
    path: Path
    actions: set[str]
    violations: list[str] = field(default_factory=list)
    input_files: list[str] = field(default_factory=list)


def actions_for(permissions: list[dict]) -> set[str]:
    out: set[str] = set()
    for p in permissions or []:
        for a in p.get("actions", []):
            out.add(a)
    return out


def make_workspace(
    permissions: list[dict],
    files: list[str] | None = None,
    skill_path: Path | None = None,
    base_dir: Path | None = None,
) -> Workspace:
    path = Path(tempfile.mkdtemp(prefix="skill-eval-", dir=str(base_dir) if base_dir else None))
    copied: list[str] = []
    for rel in files or []:
        src = (skill_path / rel) if skill_path else Path(rel)
        if src.exists():
            dest = path / Path(rel).name
            shutil.copy2(src, dest)
            copied.append(dest.name)
    return Workspace(path=path, actions=actions_for(permissions), input_files=copied)


def cleanup(ws: Workspace, keep: bool = False) -> None:
    if not keep:
        shutil.rmtree(ws.path, ignore_errors=True)


def run_command(cmd: str, cwd: Path, timeout_s: int = 60) -> tuple[int, str]:
    for pat in DESTRUCTIVE_PATTERNS:
        if re.search(pat, cmd, re.IGNORECASE):
            raise DestructiveCommandError(f"blocked destructive command: {cmd!r}")
    env = {"PATH": "/usr/bin:/bin:/usr/local/bin", "HOME": str(cwd)}
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            cwd=str(cwd),
            env=env,
            capture_output=True,
            text=True,
            timeout=timeout_s,
        )
        return proc.returncode, (proc.stdout + proc.stderr)[:8000]
    except subprocess.TimeoutExpired:
        return 124, f"timed out after {timeout_s}s"


def _safe_join(ws: Path, rel: str) -> Path:
    target = (ws / rel).resolve()
    if not str(target).startswith(str(ws.resolve())):
        raise ValueError(f"path escapes workspace: {rel}")
    return target


def build_tools(ws: Workspace, trajectory: Trajectory, full_surface: bool = False) -> list:
    from langchain_core.tools import StructuredTool

    full = {"read", "write", "create", "delete", "list", "execute"}
    allowed = full if full_surface else ws.actions
    tools: list = []

    def _record(name: str, args: dict, output: str, exit_code: int | None = None) -> str:
        trajectory.add(TrajectoryEvent(kind="tool", name=name, args=args, output=output[:2000]))
        return output

    if "read" in allowed:

        def read_file(path: str) -> str:
            try:
                return _record(
                    "read_file",
                    {"path": path},
                    _safe_join(ws.path, path).read_text(encoding="utf-8", errors="replace"),
                )
            except Exception as e:
                return _record("read_file", {"path": path}, f"error: {e}")

        tools.append(
            StructuredTool.from_function(
                read_file, name="read_file", description="Read a file from the workspace."
            )
        )

    if "list" in allowed:

        def list_dir(path: str = ".") -> str:
            try:
                base = _safe_join(ws.path, path)
                return _record(
                    "list_dir",
                    {"path": path},
                    "\n".join(sorted(p.name for p in base.iterdir())),
                )
            except Exception as e:
                return _record("list_dir", {"path": path}, f"error: {e}")

        tools.append(
            StructuredTool.from_function(
                list_dir, name="list_dir", description="List a directory in the workspace."
            )
        )

    if {"write", "create"} & allowed:

        def write_file(path: str, content: str) -> str:
            try:
                target = _safe_join(ws.path, path)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(content, encoding="utf-8")
                return _record("write_file", {"path": path}, f"wrote {len(content)} bytes")
            except Exception as e:
                return _record("write_file", {"path": path}, f"error: {e}")

        tools.append(
            StructuredTool.from_function(
                write_file, name="write_file", description="Write a file in the workspace."
            )
        )

    if "execute" in allowed:

        def run_command_tool(command: str) -> str:
            try:
                code, out = run_command(command, ws.path)
            except DestructiveCommandError as e:
                ws.violations.append(str(e))
                return f"refused: {e}"
            trajectory.add(
                TrajectoryEvent(kind="command", name=command, output=out[:2000], exit_code=code)
            )
            return f"exit={code}\n{out}"

        tools.append(
            StructuredTool.from_function(
                run_command_tool,
                name="run_command",
                description="Run a shell command in the workspace.",
            )
        )

    return tools
