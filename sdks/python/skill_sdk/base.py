from abc import ABC, abstractmethod
from .context import SkillContext, SkillEvent, SkillCommand, SkillResult, HealthStatus


class BaseSkill(ABC):
    name: str
    version: str
    skill_id: str = ""

    @abstractmethod
    async def initialize(self, ctx: SkillContext) -> None:
        ...

    @abstractmethod
    async def handle_event(self, event: SkillEvent) -> SkillResult:
        ...

    @abstractmethod
    async def handle_command(self, command: SkillCommand) -> SkillResult:
        ...

    @abstractmethod
    async def health_check(self) -> HealthStatus:
        ...

    @abstractmethod
    async def shutdown(self) -> None:
        ...
