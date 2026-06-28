"""Domain event names (PRD §06). Kept as constants to avoid stringly-typed drift."""

from __future__ import annotations

from enum import StrEnum


class EventType(StrEnum):
    WORKSPACE_CREATED = "WorkspaceCreated"
    WORKSPACE_UPDATED = "WorkspaceUpdated"
    WORKSPACE_DELETED = "WorkspaceDeleted"
    FOLDER_CREATED = "FolderCreated"
    FOLDER_UPDATED = "FolderUpdated"
    FOLDER_MOVED = "FolderMoved"
    FOLDER_DELETED = "FolderDeleted"
    OKF_IMPORTED = "OKFImported"
    KNOWLEDGE_UPDATED = "KnowledgeUpdated"
    SKILL_CREATED = "SkillCreated"
    SKILL_UPDATED = "SkillUpdated"
    SKILL_PUBLISHED = "SkillPublished"
    SKILL_DELETED = "SkillDeleted"
    SKILL_CLONED = "SkillCloned"
