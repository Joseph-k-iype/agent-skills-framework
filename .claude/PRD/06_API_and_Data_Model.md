# 06_API_and_Data_Model.md

# API & Data Model Specification

Version: 1.0

## Purpose

This document defines the canonical API contracts and data models for
EAKSO. It is the implementation contract between the React frontend and
the FastAPI backend.

------------------------------------------------------------------------

# API Standards

Base Path

    /api/v1

Standards

-   RESTful APIs
-   JSON only
-   UTF-8
-   ISO8601 timestamps
-   UUID identifiers
-   Cursor pagination
-   Optimistic concurrency
-   Pydantic request/response models
-   OpenAPI generated from FastAPI

------------------------------------------------------------------------

# Authentication

-   LDAP authentication
-   JWT access tokens
-   Refresh tokens
-   RBAC authorization
-   Resource-level permission checks

------------------------------------------------------------------------

# Standard Response

``` json
{
  "success": true,
  "data": {},
  "meta": {},
  "errors": []
}
```

------------------------------------------------------------------------

# Standard Error

``` json
{
  "success": false,
  "error": {
    "code": "SKILL_NOT_FOUND",
    "message": "Skill does not exist.",
    "trace_id": "uuid"
  }
}
```

------------------------------------------------------------------------

# Core Data Models

## Workspace

Fields

-   id
-   name
-   description
-   owner_id
-   created_at
-   updated_at

------------------------------------------------------------------------

## Folder

Fields

-   id
-   workspace_id
-   parent_folder_id
-   name
-   path
-   description
-   permissions

------------------------------------------------------------------------

## Skill

Fields

-   id
-   folder_id
-   name
-   description
-   runtime
-   version
-   status
-   capability_ids
-   okf_references
-   workflow_id
-   evaluation_id

------------------------------------------------------------------------

## Workflow

Fields

-   id
-   folder_id
-   name
-   description
-   reactflow_json
-   version
-   status

------------------------------------------------------------------------

## Agent

Fields

-   id
-   name
-   type
-   description
-   langgraph_definition
-   tools
-   version

------------------------------------------------------------------------

## OKF Document Reference

Fields

-   id
-   title
-   relative_path
-   source_repository
-   graph_node_id

------------------------------------------------------------------------

## Evaluation

Fields

-   id
-   skill_id
-   overall_score
-   security_score
-   performance_score
-   documentation_score
-   governance_score
-   recommendations

------------------------------------------------------------------------

## Execution

Fields

-   id
-   workflow_id
-   started_at
-   completed_at
-   status
-   duration_ms
-   token_usage
-   cost

------------------------------------------------------------------------

# REST Endpoints

## Workspace

GET /workspaces

POST /workspaces

GET /workspaces/{id}

PATCH /workspaces/{id}

DELETE /workspaces/{id}

------------------------------------------------------------------------

## Folder

GET /folders/{id}

POST /folders

PATCH /folders/{id}

DELETE /folders/{id}

POST /folders/{id}/move

------------------------------------------------------------------------

## Skills

GET /skills

POST /skills

GET /skills/{id}

PATCH /skills/{id}

DELETE /skills/{id}

POST /skills/{id}/publish

POST /skills/{id}/clone

POST /skills/{id}/evaluate

------------------------------------------------------------------------

## Workflows

GET /workflows

POST /workflows

PATCH /workflows/{id}

POST /workflows/{id}/validate

POST /workflows/{id}/execute

------------------------------------------------------------------------

## Knowledge Graph

GET /graph/node/{id}

GET /graph/search

GET /graph/traverse

GET /graph/lineage

GET /graph/similar

------------------------------------------------------------------------

## Marketplace

GET /marketplace

GET /marketplace/trending

GET /marketplace/featured

POST /marketplace/publish

------------------------------------------------------------------------

## Evaluator

POST /evaluations/run

GET /evaluations/{id}

GET /evaluations/history

------------------------------------------------------------------------

## Search

GET /search

Parameters

-   q
-   workspace
-   folder
-   type
-   tags
-   limit

Returns hybrid graph search results.

------------------------------------------------------------------------

# Domain Events

Events are immutable.

Core events

-   WorkspaceCreated
-   FolderCreated
-   FolderMoved
-   SkillCreated
-   SkillUpdated
-   SkillPublished
-   WorkflowCreated
-   WorkflowExecuted
-   EvaluationCompleted
-   MarketplacePublished
-   KnowledgeUpdated

------------------------------------------------------------------------

# Event Payload

``` json
{
  "event_id":"uuid",
  "event_type":"SkillCreated",
  "occurred_at":"timestamp",
  "actor":"user",
  "resource_id":"uuid",
  "workspace_id":"uuid"
}
```

------------------------------------------------------------------------

# Pagination

Cursor based.

``` json
{
  "items":[],
  "next_cursor":"..."
}
```

------------------------------------------------------------------------

# Validation Rules

-   UUID validation
-   Required fields
-   Unique paths
-   RBAC validation
-   Workspace ownership
-   Folder hierarchy integrity
-   Workflow validation before publish

------------------------------------------------------------------------

# Acceptance Criteria

-   Every resource has CRUD APIs.
-   APIs are versioned.
-   Data contracts are shared through Pydantic.
-   Events are emitted for every mutation.
-   All endpoints enforce RBAC.
-   Responses follow the standard envelope.
