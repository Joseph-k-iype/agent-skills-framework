"""Canonical FalkorDB ontology — node labels, relationship types, common props.

Derived from PRD docs 01 (Product Architecture) and 05 (Knowledge Graph & OKF).
Phase 0–3 actively use a subset; the rest are reserved so later phases don't
require a schema migration.
"""

from __future__ import annotations

from enum import StrEnum


class NodeLabel(StrEnum):
    # Active in Phases 0–3
    WORKSPACE = "Workspace"
    KNOWLEDGE_PACKAGE = "KnowledgePackage"
    FOLDER = "Folder"
    SKILL = "Skill"
    OKF_DOCUMENT = "OKFDocument"
    # A Concept is one OKF markdown file projected from the workspace bundle.
    # It is the unified node for skills/agents/prompts/docs (type is free text).
    CONCEPT = "Concept"
    CAPABILITY = "Capability"
    SOURCE = "Source"
    # A published snapshot of a Concept (one per git tag).
    VERSION = "Version"
    # Reserved for later phases
    WORKFLOW = "Workflow"
    AGENT = "Agent"
    PROMPT = "Prompt"
    EXECUTION = "Execution"
    EVALUATION = "Evaluation"


class RelType(StrEnum):
    CONTAINS = "CONTAINS"
    PARENT_OF = "PARENT_OF"
    CHILD_OF = "CHILD_OF"
    HAS_SKILL = "HAS_SKILL"
    HAS_DOCUMENT = "HAS_DOCUMENT"
    REFERENCES = "REFERENCES"
    RELATED_TO = "RELATED_TO"
    BELONGS_TO = "BELONGS_TO"
    DEPENDS_ON = "DEPENDS_ON"
    USES = "USES"
    DERIVED_FROM = "DERIVED_FROM"
    OWNS = "OWNS"
    PREVIOUS_VERSION = "PREVIOUS_VERSION"
    HAS_VERSION = "HAS_VERSION"


# Labels whose nodes carry a vector `embedding` property (semantic search).
EMBEDDABLE_LABELS: tuple[NodeLabel, ...] = (
    NodeLabel.OKF_DOCUMENT,
    NodeLabel.CONCEPT,
    NodeLabel.SKILL,
    NodeLabel.CAPABILITY,
)

# Common properties present on every node.
COMMON_PROPS: tuple[str, ...] = (
    "id",
    "name",
    "type",
    "description",
    "version",
    "workspace_id",
    "path",
    "tags",
    "owner",
    "status",
    "created_at",
    "updated_at",
)
