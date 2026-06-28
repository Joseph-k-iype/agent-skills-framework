"""Skill business logic: CRUD, references, capabilities, version lineage, clone."""

from __future__ import annotations

import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import CurrentUser
from app.api.errors import ConflictError, NotFoundError, ValidationError
from app.events.types import EventType
from app.repositories.skill_graph_repo import SkillGraphRepository
from app.schemas.skill import (
    SkillClone,
    SkillCreate,
    SkillOut,
    SkillPublish,
    SkillUpdate,
    SkillVersions,
)
from app.services.audit_service import AuditService

_SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _new_id() -> str:
    return uuid.uuid4().hex


def _slug(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", name.strip().lower()).strip("-")


def _semver(v: str) -> tuple[int, int, int]:
    m = _SEMVER.match(v)
    if not m:
        raise ValidationError(f"Invalid semantic version: {v}")
    return int(m[1]), int(m[2]), int(m[3])


class SkillService:
    def __init__(self, db: AsyncSession, user: CurrentUser):
        self.db = db
        self.user = user
        self.repo = SkillGraphRepository()
        self.audit = AuditService(db)

    def _require(self, skill_id: str) -> dict:
        s = self.repo.get_skill(skill_id)
        if s is None:
            raise NotFoundError("Skill not found")
        return s

    async def create(self, body: SkillCreate) -> SkillOut:
        node = self.repo.create_skill(
            id=_new_id(),
            skill_key=f"{_slug(body.name)}-{_new_id()[:6]}",
            name=body.name,
            description=body.description,
            runtime=body.runtime,
            version="0.1.0",
            workspace_id=body.workspace_id,
            folder_id=body.folder_id,
            tags=body.tags,
            capabilities=body.capabilities,
            ts=_now(),
        )
        if node is None:
            raise NotFoundError("Target folder not found")
        if body.capabilities:
            self.repo.set_capabilities(id=node["id"], names=body.capabilities, ts=_now())
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.SKILL_CREATED,
            resource_type="Skill",
            resource_id=node["id"],
            workspace_id=body.workspace_id,
            payload={"name": body.name},
        )
        return self.get(node["id"])

    def list(self, *, workspace_id: str | None, folder_id: str | None, q: str | None) -> list[SkillOut]:
        nodes = self.repo.list_current(workspace_id=workspace_id, folder_id=folder_id, q=q)
        return [SkillOut(**n) for n in nodes]

    def get(self, skill_id: str) -> SkillOut:
        return SkillOut(**self._require(skill_id))

    def versions(self, skill_id: str) -> SkillVersions:
        s = self._require(skill_id)
        chain = self.repo.version_chain(s["skill_key"])
        return SkillVersions(skill_key=s["skill_key"], versions=[SkillOut(**c) for c in chain])

    async def update(self, skill_id: str, body: SkillUpdate) -> SkillOut:
        self._require(skill_id)
        ts = _now()
        self.repo.update_skill(
            id=skill_id,
            name=body.name,
            description=body.description,
            runtime=body.runtime,
            tags=body.tags,
            capabilities=body.capabilities,
            ts=ts,
        )
        if body.capabilities is not None:
            self.repo.set_capabilities(id=skill_id, names=body.capabilities, ts=ts)
        if body.references is not None:
            self.repo.set_references(id=skill_id, doc_ids=body.references)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.SKILL_UPDATED,
            resource_type="Skill",
            resource_id=skill_id,
        )
        return self.get(skill_id)

    async def publish(self, skill_id: str, body: SkillPublish) -> SkillOut:
        current = self._require(skill_id)
        target_id = skill_id

        if body.version and body.version != current["version"]:
            # creating a new published version in the lineage
            if _semver(body.version) <= _semver(current["version"]):
                raise ConflictError("New version must be greater than the current version")
            new = self.repo.create_version(
                old_id=skill_id,
                new_id=_new_id(),
                version=body.version,
                skill_key=current["skill_key"],
                ts=_now(),
            )
            if new is None:
                raise NotFoundError("Could not create version")
            target_id = new["id"]
        else:
            self.repo.set_status(id=skill_id, status="published", ts=_now())

        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.SKILL_PUBLISHED,
            resource_type="Skill",
            resource_id=target_id,
            workspace_id=current.get("workspace_id"),
            payload={"version": body.version or current["version"]},
        )
        return self.get(target_id)

    async def clone(self, skill_id: str, body: SkillClone) -> SkillOut:
        src = self._require(skill_id)
        name = body.name or f"{src['name']} (copy)"
        node = self.repo.clone_skill(
            src_id=skill_id,
            new_id=_new_id(),
            skill_key=f"{_slug(name)}-{_new_id()[:6]}",
            name=name,
            folder_id=body.folder_id,
            ts=_now(),
        )
        if node is None:
            raise NotFoundError("Target folder not found")
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.SKILL_CLONED,
            resource_type="Skill",
            resource_id=node["id"],
            payload={"from": skill_id},
        )
        return self.get(node["id"])

    async def delete(self, skill_id: str) -> None:
        s = self._require(skill_id)
        self.repo.delete_skill(skill_id)
        await self.audit.record(
            actor_id=self.user.id,
            action=EventType.SKILL_DELETED,
            resource_type="Skill",
            resource_id=skill_id,
            workspace_id=s.get("workspace_id"),
        )
