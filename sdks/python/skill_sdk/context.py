from dataclasses import dataclass, field
from typing import Any


@dataclass
class SkillEvent:
    name: str
    payload: dict[str, Any] = field(default_factory=dict)
    source: str = ""


@dataclass
class SkillCommand:
    name: str
    args: list[str] = field(default_factory=list)
    kwargs: dict[str, str] = field(default_factory=dict)
    payload: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillResult:
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    message: str = ""


@dataclass
class HealthStatus:
    healthy: bool = True
    version: str = ""
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillContext:
    config: dict[str, Any] = field(default_factory=dict)
    logger: Any = None
    registry: Any = None
    state: dict[str, Any] = field(default_factory=dict)
    graph: Any = None
