# 08_Database_and_Ontology_Specification.md

# Database & Ontology Specification

Version: 1.0

## Purpose

Defines the canonical persistence model for EAKSO. This document is the
single source of truth for PostgreSQL, FalkorDB, ontology, graph
relationships, indexing and graph mutation rules.

------------------------------------------------------------------------

# Persistence Strategy

## PostgreSQL

Stores operational data.

-   Users
-   Organizations
-   Roles
-   Sessions
-   Audit Logs
-   Notifications
-   Configuration
-   Marketplace metadata

## FalkorDB

Stores semantic knowledge.

-   Workspace hierarchy
-   Folders
-   Skills
-   Workflows
-   Agents
-   OKF documents
-   Capabilities
-   Executions
-   Evaluations
-   Native embeddings
-   Relationships

------------------------------------------------------------------------

# Workspace Ontology

``` text
Workspace
 ├── Folder
 │    ├── Folder
 │    ├── Skill
 │    ├── Workflow
 │    ├── Agent
 │    ├── Prompt
 │    └── OKFDocument
```

Every object exists as a node.

------------------------------------------------------------------------

# Node Labels

## Authoring

-   Workspace
-   Folder
-   Skill
-   Workflow
-   Prompt
-   Agent

## Knowledge

-   OKFDocument
-   Domain
-   Application
-   Dataset
-   Table
-   API
-   Metric
-   Policy
-   Runbook
-   Playbook
-   GlossaryTerm
-   ArchitectureDecision

## Runtime

-   Execution
-   Evaluation
-   Capability
-   Runtime

## Identity

-   User
-   Team
-   Organization

------------------------------------------------------------------------

# Common Node Properties

-   id (UUID)
-   name
-   path
-   description
-   status
-   version
-   owner_id
-   workspace_id
-   tags
-   embedding
-   created_at
-   updated_at

------------------------------------------------------------------------

# Relationship Types

Hierarchy

-   CONTAINS
-   PARENT_OF
-   CHILD_OF

Knowledge

-   REFERENCES
-   DEFINES
-   RELATED_TO
-   BELONGS_TO

Execution

-   EXECUTES
-   USES
-   DEPENDS_ON
-   PRODUCES
-   CONSUMES

Governance

-   OWNS
-   REVIEWED_BY
-   APPROVED_BY
-   EVALUATED_BY

Similarity

-   SIMILAR_TO

------------------------------------------------------------------------

# Graph Constraints

-   Every node has a UUID.
-   Every node belongs to exactly one Workspace.
-   Folder paths are unique within a Workspace.
-   No circular folder hierarchy.
-   Relationships are typed.
-   Every relationship stores created_at.

------------------------------------------------------------------------

# Embeddings

Embeddings are stored directly on nodes.

Indexed node types:

-   Skill
-   Workflow
-   Prompt
-   OKFDocument
-   Policy
-   API
-   Dataset
-   GlossaryTerm
-   Capability

Embeddings are regenerated after meaningful content changes.

------------------------------------------------------------------------

# Hybrid Retrieval

1.  Embed query.
2.  Vector similarity search.
3.  Expand graph.
4.  Remove duplicates.
5.  Rank by:
    -   similarity
    -   graph distance
    -   workspace proximity
    -   evaluation score
6.  Return explainable context.

------------------------------------------------------------------------

# OKF Ingestion Mapping

Markdown document → Parse YAML frontmatter → Create/Update OKFDocument
node → Create referenced domain entities → Resolve markdown links →
Create REFERENCES relationships → Generate embedding → Index node

------------------------------------------------------------------------

# Graph Mutation Rules

Workspace Created

-   Create Workspace node.

Folder Created

-   Create Folder node.
-   Link with CONTAINS.

Skill Created

-   Create Skill node.
-   Link Folder → Skill.
-   Link Skill → referenced OKFDocument.

Workflow Published

-   Create version node.
-   Update EXECUTES relationships.

Execution Completed

-   Create Execution node.
-   Link Skill/Workflow.
-   Store metrics.

Evaluation Completed

-   Create Evaluation node.
-   Link EVALUATED_BY.

------------------------------------------------------------------------

# Versioning

Current version:

LATEST

Historical versions:

PREVIOUS_VERSION

Superseded:

REPLACES

Deprecated:

DEPRECATED_BY

No graph history is deleted.

------------------------------------------------------------------------

# Suggested Indexes

Unique

-   Workspace.id
-   Folder.id
-   Skill.id
-   Workflow.id
-   OKFDocument.id

Lookup

-   path
-   name
-   tags
-   owner_id
-   version

Vector

-   embedding

------------------------------------------------------------------------

# Query Patterns

## Workspace Explorer

Workspace → CONTAINS → Folder → Folder → Skill

## Impact Analysis

Skill ← REFERENCES ← Workflow ← Agent

## Semantic Search

Embedding → Similar Nodes → Expand Relationships → Return Context

## Lineage

Current Node ← PREVIOUS_VERSION* → REPLACES*

------------------------------------------------------------------------

# Event to Graph Mapping

  Event                 Graph Mutation
  --------------------- -------------------------
  WorkspaceCreated      Create Workspace
  FolderCreated         Create Folder
  FolderMoved           Update Parent
  SkillCreated          Create Skill
  SkillPublished        Update Version
  OKFImported           Create/Update Knowledge
  EvaluationCompleted   Create Evaluation
  ExecutionCompleted    Create Execution

------------------------------------------------------------------------

# Acceptance Criteria

-   PostgreSQL stores operational state only.
-   FalkorDB stores semantic state only.
-   Every asset has a graph node.
-   Every graph node has lineage.
-   Every mutation updates the graph.
-   Embeddings are stored natively in FalkorDB.
-   Search is graph-first with semantic ranking.
