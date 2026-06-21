from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class TrajectoryEvent:
    kind: str  # "tool" | "command"
    name: str  # tool name, or the command string for commands
    args: dict[str, Any] = field(default_factory=dict)
    output: str = ""
    exit_code: int | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "name": self.name,
            "args": self.args,
            "output": self.output,
            "exit_code": self.exit_code,
        }


@dataclass
class Trajectory:
    events: list[TrajectoryEvent] = field(default_factory=list)
    tokens_in: int = 0
    tokens_out: int = 0
    duration_ms: int = 0

    def add(self, event: TrajectoryEvent) -> None:
        self.events.append(event)

    def commands(self) -> list[TrajectoryEvent]:
        return [e for e in self.events if e.kind == "command"]

    def to_dict(self) -> dict[str, Any]:
        return {
            "events": [e.to_dict() for e in self.events],
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "duration_ms": self.duration_ms,
        }


@dataclass
class RunResult:
    final_text: str = ""
    workspace_path: str = ""
    trajectory: Trajectory = field(default_factory=Trajectory)
    permission_violations: list[str] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "final_text": self.final_text,
            "workspace_path": self.workspace_path,
            "trajectory": self.trajectory.to_dict(),
            "permission_violations": self.permission_violations,
            "error": self.error,
        }
