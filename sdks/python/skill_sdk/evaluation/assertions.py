from __future__ import annotations

import fnmatch
import re
from pathlib import Path
from typing import Any

from .trajectory import RunResult


def _match_pattern(text: str, pattern: str) -> bool:
    """A /slash-wrapped/ pattern is a regex; anything else is a substring."""
    if len(pattern) >= 2 and pattern.startswith("/") and pattern.endswith("/"):
        return re.search(pattern[1:-1], text) is not None
    return pattern in text


def _workspace_files(ws: Path) -> list[str]:
    return [str(p.relative_to(ws)) for p in ws.rglob("*") if p.is_file()]


def _file_exists(ws: Path, spec: dict) -> tuple[bool, str]:
    pattern = spec.get("path", "")
    matches = fnmatch.filter(_workspace_files(ws), pattern)
    if matches:
        return True, f"matched {matches[:5]}"
    return False, f"no file matched '{pattern}'"


def _file_contains(ws: Path, spec: dict) -> tuple[bool, str]:
    pattern = spec.get("path", "")
    text = spec.get("text")
    rx = spec.get("pattern")
    for rel in fnmatch.filter(_workspace_files(ws), pattern):
        content = (ws / rel).read_text(encoding="utf-8", errors="replace")
        if text is not None and text in content:
            return True, f"'{text}' found in {rel}"
        if rx is not None and re.search(rx, content):
            return True, f"/{rx}/ matched in {rel}"
    needle = text if text is not None else f"/{rx}/"
    return False, f"{needle!r} not found in any '{pattern}'"


def _command_ran(res: RunResult, spec: dict) -> tuple[bool, str]:
    pattern = spec.get("pattern", "")
    for ev in res.trajectory.commands():
        if _match_pattern(ev.name, pattern):
            return True, f"command '{ev.name}' matched"
    return False, f"no command matched '{pattern}'"


def _exit_code(res: RunResult, spec: dict) -> tuple[bool, str]:
    equals = spec.get("equals")
    cmd_pat = spec.get("command")
    cmds = res.trajectory.commands()
    if cmd_pat:
        cmds = [c for c in cmds if _match_pattern(c.name, cmd_pat)]
    if not cmds:
        return False, f"no command matched '{cmd_pat}'"
    last = cmds[-1]
    ok = last.exit_code == equals
    return ok, f"'{last.name}' exited {last.exit_code} (wanted {equals})"


def _no_extra_files(ws: Path, spec: dict, input_files: list[str]) -> tuple[bool, str]:
    allow = list(spec.get("allow", [])) + [Path(f).name for f in input_files] + list(input_files)
    extras = []
    for rel in _workspace_files(ws):
        if any(fnmatch.fnmatch(rel, pat) for pat in allow):
            continue
        extras.append(rel)
    if extras:
        return False, f"unexpected files: {sorted(extras)[:10]}"
    return True, "no files beyond inputs + allowlist"


def evaluate_assertions(
    case: dict[str, Any], result: RunResult, input_files: list[str] | None = None
) -> list[dict[str, Any]]:
    input_files = input_files or []
    ws = Path(result.workspace_path) if result.workspace_path else None
    out: list[dict[str, Any]] = []
    for spec in case.get("expect", {}).get("assertions", []):
        kind = spec.get("kind")
        if kind == "llm":
            continue
        try:
            if kind == "file_exists":
                passed, evidence = _file_exists(ws, spec)
            elif kind == "file_contains":
                passed, evidence = _file_contains(ws, spec)
            elif kind == "command_ran":
                passed, evidence = _command_ran(result, spec)
            elif kind == "exit_code":
                passed, evidence = _exit_code(result, spec)
            elif kind == "no_extra_files":
                passed, evidence = _no_extra_files(ws, spec, input_files)
            else:
                passed, evidence = False, f"unknown kind '{kind}'"
        except Exception as e:  # a malformed workspace must not crash the suite
            passed, evidence = False, f"{type(e).__name__}: {e}"
        out.append({"kind": kind, "spec": spec, "passed": passed, "evidence": evidence})
    return out
