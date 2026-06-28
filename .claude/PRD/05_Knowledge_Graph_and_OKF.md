# 05_Knowledge_Graph_and_OKF.md

# Knowledge Graph & Open Knowledge Format Specification

Version: 1.0

## Purpose

This document defines the canonical knowledge model for the Enterprise
AI Knowledge & Skills Operating System (EAKSO).

It specifies:

-   Google Open Knowledge Format (OKF)
-   FalkorDB ontology
-   Workspace ↔ OKF mapping
-   Graph schema
-   Semantic retrieval
-   Knowledge lifecycle
-   Versioning
-   Validation

------------------------------------------------------------------------

# What is OKF?

The Open Knowledge Format (OKF) is an open convention introduced by
Google Cloud for representing organizational knowledge in a form that is
readable by both humans and AI systems.

OKF is based on:

-   Markdown documents
-   YAML frontmatter
-   Directory hierarchy
-   Markdown hyperlinks
-   Git version control

OKF is intentionally simple. It does not define execution logic or
workflows. It standardizes how enterprise knowledge is documented and
connected.

------------------------------------------------------------------------

# EAKSO Knowledge Model

EAKSO does not replace OKF.

Instead it:

1.  Reads OKF documents.
2.  Parses metadata from YAML frontmatter.
3.  Resolves document links.
4.  Builds a semantic graph in FalkorDB.
5.  Generates embeddings for graph nodes.
6.  Enables semantic retrieval and reasoning.

OKF remains the source of truth.

FalkorDB is the runtime knowledge representation.

------------------------------------------------------------------------

# Workspace Mapping

Workspace └── Folder ├── Skill ├── Workflow ├── Prompt ├── OKF Document
└── Agent

The folder hierarchy mirrors the logical organization of enterprise
knowledge. Every asset has a corresponding node in FalkorDB.

------------------------------------------------------------------------

# FalkorDB Node Types

Core

-   Workspace
-   Folder
-   Skill
-   Workflow
-   Agent
-   Prompt
-   OKFDocument
-   Capability
-   Execution
-   Evaluation

Enterprise

-   Domain
-   Application
-   API
-   Dataset
-   Table
-   Metric
-   Policy
-   Runbook
-   Playbook
-   GlossaryTerm
-   ArchitectureDecision

Identity

-   User
-   Team
-   Organization

------------------------------------------------------------------------

# Relationship Types

Hierarchy

-   CONTAINS
-   PARENT_OF
-   CHILD_OF

Knowledge

-   REFERENCES
-   RELATED_TO
-   BELONGS_TO
-   DEFINES

Execution

-   EXECUTES
-   USES
-   DEPENDS_ON
-   GENERATES

Governance

-   OWNS
-   APPROVED_BY
-   REVIEWED_BY
-   EVALUATED_BY

------------------------------------------------------------------------

# Node Properties

Every node includes:

-   id
-   name
-   type
-   description
-   version
-   workspace_id
-   path
-   tags
-   owner
-   created_at
-   updated_at
-   embedding
-   status

Additional properties are defined per node type.

------------------------------------------------------------------------

# Embedding Strategy

Embeddings are stored directly on FalkorDB nodes.

Embedding targets include:

-   OKF documents
-   Skills
-   Workflows
-   Prompts
-   Glossary terms
-   Policies
-   APIs
-   Datasets

Embeddings are regenerated when knowledge changes.

------------------------------------------------------------------------

# Semantic Retrieval

Pipeline

1.  Embed user query.
2.  Vector similarity search.
3.  Graph expansion.
4.  Relationship ranking.
5.  Context assembly.
6.  Return explainable results.

Returned context always includes provenance to originating OKF
documents.

------------------------------------------------------------------------

# Graph Traversal

Traversal priorities

1.  Current workspace
2.  Folder hierarchy
3.  Referenced OKF documents
4.  Dependencies
5.  Related capabilities
6.  Similar assets

Traversal depth is configurable.

------------------------------------------------------------------------

# Knowledge Lifecycle

Author → Commit OKF → Import → Validation → Graph Update → Embedding
Refresh → Search Available → Skill References → Agent Consumption

------------------------------------------------------------------------

# Versioning

Knowledge versions follow Git.

Graph nodes retain:

-   current version
-   previous version
-   lineage
-   deprecation status

Relationships are version-aware.

------------------------------------------------------------------------

# Validation Rules

OKF

-   Valid Markdown
-   Valid YAML
-   Unique identifiers
-   No broken links
-   Required metadata

Graph

-   No orphan nodes
-   No circular folder hierarchy
-   Valid relationships
-   Unique paths
-   Referential integrity

------------------------------------------------------------------------

# Explainability

Every recommendation must expose:

-   Retrieved nodes
-   Traversed relationships
-   Referenced OKF documents
-   Ranking rationale

No graph-derived answer is returned without provenance.

------------------------------------------------------------------------

# Acceptance Criteria

-   OKF remains the authoritative knowledge source.
-   Every Workspace asset has a graph node.
-   Folder hierarchy is preserved in FalkorDB.
-   Embeddings are stored natively on graph nodes.
-   Semantic search combines vector similarity and graph traversal.
-   All graph mutations preserve lineage and provenance.
