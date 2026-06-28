# 03_Backend_Architecture.md

# Backend Architecture Specification

Version: 1.0

## Purpose

This document defines the backend architecture for the Enterprise AI
Knowledge & Skills Operating System (EAKSO). It serves as the
implementation specification for Python engineers and AI coding
assistants.

------------------------------------------------------------------------

# Technology Stack

## Language

-   Python 3.12+

## Frameworks

-   FastAPI
-   Pydantic v2
-   SQLAlchemy
-   Alembic
-   Celery
-   Redis

## Storage

-   PostgreSQL (relational data)
-   FalkorDB (knowledge graph, native embeddings, semantic search)

## AI

-   OpenRouter
-   LangGraph
-   Instructor
-   PydanticAI

------------------------------------------------------------------------

# Architectural Principles

-   Domain-driven design
-   Service-oriented architecture
-   Event-driven workflows
-   Async-first APIs
-   Repository pattern
-   Strict typing
-   Stateless API layer
-   Graph-native knowledge model

------------------------------------------------------------------------

# High-Level Services

-   API Gateway
-   Workspace Service
-   Knowledge Service
-   OKF Service
-   Skill Service
-   Workflow Service
-   Agent Service
-   Evaluation Service
-   Marketplace Service
-   Search Service
-   Execution Service
-   Analytics Service
-   Notification Service

Each service exposes internal service methods and REST endpoints.

------------------------------------------------------------------------

# Suggested Repository Layout

``` text
backend/
├── app/
│   ├── api/
│   ├── core/
│   ├── config/
│   ├── auth/
│   ├── services/
│   ├── repositories/
│   ├── models/
│   ├── schemas/
│   ├── graph/
│   ├── agents/
│   ├── workflows/
│   ├── events/
│   ├── tasks/
│   ├── search/
│   ├── marketplace/
│   └── utils/
├── tests/
└── migrations/
```

------------------------------------------------------------------------

# Data Ownership

## PostgreSQL

-   Users
-   Organizations
-   Roles
-   Permissions
-   Sessions
-   Audit Logs
-   Notifications
-   Configuration
-   Marketplace metadata

## FalkorDB

-   Workspace hierarchy
-   Knowledge Packages
-   Folders
-   Skills
-   Workflows
-   OKF documents
-   Agents
-   Capabilities
-   Relationships
-   Executions
-   Evaluations
-   Native embeddings

------------------------------------------------------------------------

# Request Flow

``` text
React Client
      │
FastAPI Router
      │
Service Layer
      │
Repository Layer
      ├── PostgreSQL
      └── FalkorDB
```

Business logic resides only in the service layer.

------------------------------------------------------------------------

# Event Bus

Every state change emits an event.

Core events:

-   WorkspaceCreated
-   FolderCreated
-   SkillCreated
-   SkillUpdated
-   SkillPublished
-   WorkflowCreated
-   WorkflowExecuted
-   OKFImported
-   GraphUpdated
-   EvaluationCompleted
-   MarketplacePublished

Celery workers subscribe to events for asynchronous processing.

------------------------------------------------------------------------

# Search Pipeline

1.  Generate query embedding.
2.  Execute FalkorDB vector similarity search.
3.  Expand related nodes through graph traversal.
4.  Rank results using graph proximity and relevance.
5.  Return explainable search results.

No external vector database is used.

------------------------------------------------------------------------

# Background Jobs

Celery tasks include:

-   OKF ingestion
-   Embedding generation
-   Graph synchronization
-   Evaluation
-   Workflow execution
-   Notification delivery
-   Marketplace indexing
-   Analytics aggregation

------------------------------------------------------------------------

# API Standards

-   RESTful endpoints
-   Versioned APIs (/api/v1)
-   JSON only
-   Pydantic request/response models
-   Consistent error model
-   Cursor-based pagination
-   OpenAPI documentation generated automatically

------------------------------------------------------------------------

# Security

-   LDAP authentication
-   RBAC authorization
-   Resource-level permissions
-   Audit every mutation
-   Input validation
-   Rate limiting
-   Structured logging

------------------------------------------------------------------------

# Observability

-   OpenTelemetry tracing
-   Structured logs
-   Health endpoints
-   Metrics endpoints
-   Correlation IDs

------------------------------------------------------------------------

# Coding Standards

## Python

-   Black
-   Ruff
-   mypy
-   pytest
-   Async where applicable
-   Dependency injection
-   No ORM objects outside repositories

## FastAPI

-   One router per domain
-   One service per aggregate
-   One repository per persistence model

------------------------------------------------------------------------

# Acceptance Criteria

-   Clear separation of API, service and repository layers.
-   FalkorDB is the authoritative graph and semantic search engine.
-   PostgreSQL stores operational metadata only.
-   All long-running work executes asynchronously through Celery.
-   Every mutation emits a domain event.
-   Services are independently testable.
-   APIs are fully typed and documented.
