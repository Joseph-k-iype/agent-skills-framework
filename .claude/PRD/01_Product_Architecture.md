# 01_Product_Architecture.md

# Enterprise AI Knowledge & Skills Operating System

## Product Architecture Specification

Version: 1.1

------------------------------------------------------------------------

# Purpose

This document defines the application architecture for the Enterprise AI
Knowledge & Skills Operating System (EAKSO). It is intended to be
consumed directly by AI coding assistants and engineers.

The application is built around a **Workspace** rather than a flat Skill
Registry.

The Workspace mirrors the OKF directory hierarchy and is represented
one-to-one inside FalkorDB.

------------------------------------------------------------------------

# Technology Stack

## Frontend

-   React 19
-   Vite
-   TypeScript
-   Ant Design
-   React Router
-   React Flow
-   TanStack Query
-   Zustand

## Backend

-   Python
-   FastAPI
-   PostgreSQL
-   FalkorDB
-   Redis
-   Celery

## AI

-   OpenRouter
-   LangGraph
-   PydanticAI
-   Instructor

Authentication: LDAP only.

------------------------------------------------------------------------

# Core Principles

-   Workspace-first architecture
-   OKF-compliant directory hierarchy
-   Graph-native storage
-   Event-driven backend
-   RBAC on every resource
-   API-first design
-   Python backend
-   React + TypeScript frontend

------------------------------------------------------------------------

# RBAC

## Consumer

Marketplace experience with a top navigation.

Access: - Marketplace - Search - Categories - Collections - Skill
Details - Reviews - Profile

No authoring capabilities.

## Developer

Dashboard experience with left sidebar.

Access: - Dashboard - Workspace - Create Skill - Workflow Builder -
Knowledge Graph - Evaluator - Executions - Analytics - Community

## Admin

Enterprise control plane.

Additional access: - Users - Roles - Organizations - Taxonomies -
Categories - Capabilities - Marketplace Moderation - Audit Logs - System
Health - Settings

------------------------------------------------------------------------

# Workspace

The Workspace replaces the traditional Skill Registry.

Everything lives inside a hierarchical directory structure.

``` text
Workspace
│
├── Knowledge Package
│   ├── Folder
│   │   ├── Folder
│   │   │   ├── Skill
│   │   │   ├── Workflow
│   │   │   ├── OKF Document
│   │   │   ├── Prompt
│   │   │   └── Agent
│   │   └── Folder
│   └── Folder
└── Knowledge Package
```

The directory hierarchy is the source of truth for organization and must
be reflected in FalkorDB.

------------------------------------------------------------------------

# Knowledge Packages

A Knowledge Package maps to an OKF package.

Examples:

-   Finance
-   Sales
-   Customer360
-   Risk
-   Compliance

Each package contains folders, skills, workflows and OKF documents.

------------------------------------------------------------------------

# Folder Capabilities

Folders support:

-   Create
-   Rename
-   Move
-   Delete
-   Drag & Drop
-   Version History
-   Permissions
-   Search
-   Favorites

Folders may contain:

-   Folders
-   Skills
-   Workflows
-   OKF Documents
-   Prompts
-   Agents

------------------------------------------------------------------------

# Workspace Navigation

``` text
Workspace

▼ Finance

    ▼ Payments

        Invoice OCR

        Invoice Summary

        Payment Validator

    ▼ Customers

        Customer Lookup

        KYC Workflow

▼ Sales

    Forecasting

    Reports
```

------------------------------------------------------------------------

# Graph Representation

Every directory object is represented in FalkorDB.

Node Types:

-   Workspace
-   KnowledgePackage
-   Folder
-   Skill
-   Workflow
-   Agent
-   Prompt
-   OKFDocument
-   Capability
-   Execution
-   Evaluation

Relationships:

-   CONTAINS
-   HAS_FOLDER
-   HAS_SKILL
-   HAS_WORKFLOW
-   HAS_DOCUMENT
-   PARENT_OF
-   CHILD_OF
-   REFERENCES
-   DEPENDS_ON
-   EXECUTES
-   BELONGS_TO

------------------------------------------------------------------------

# Semantic Search

Search uses FalkorDB native embeddings.

Pipeline:

1.  User query
2.  Query embedding
3.  Vector similarity
4.  Graph traversal
5.  Relationship expansion
6.  Context ranking
7.  Result explanation

Results should include sibling folders, referenced OKF documents,
dependent workflows and related skills.

------------------------------------------------------------------------

# Knowledge Graph UI

React Flow provides two modes.

## Explorer Mode

Displays the Workspace hierarchy.

## Relationship Mode

Displays semantic relationships for the selected node.

Users can switch between modes without leaving the page.

------------------------------------------------------------------------

# Workflow Builder

Built with React Flow.

Supports:

-   Folder-aware workflows
-   Nested workflows
-   Skill reuse
-   Drag & Drop
-   Conditional execution
-   Parallel branches
-   Retry policies
-   Validation

Workflows reference Skills in the Workspace rather than embedding
copies.

------------------------------------------------------------------------

# Core Modules

-   Dashboard
-   Workspace
-   Marketplace
-   Workflow Builder
-   Knowledge Graph
-   Evaluator
-   Executions
-   Analytics
-   Community
-   Administration

------------------------------------------------------------------------

# Coding Standards

## Frontend

-   React + TypeScript only
-   Functional components
-   Hooks only
-   Strict TypeScript
-   Ant Design components
-   Feature-based folder structure
-   Zustand for client state
-   TanStack Query for server state
-   Lazy-loaded routes

## Backend

-   Python only
-   FastAPI
-   Pydantic models
-   Service layer architecture
-   Repository pattern
-   Async APIs where applicable
-   Celery for background jobs
-   Event-driven domain services

Business logic must never exist in React components.

------------------------------------------------------------------------

# Acceptance Criteria

-   Workspace replaces Skill Registry everywhere.
-   Directory hierarchy maps directly to FalkorDB.
-   Every node has a graph representation.
-   React Flow supports Explorer and Relationship modes.
-   Consumer receives marketplace UI.
-   Developer/Admin receive dashboard UI.
-   Backend is implemented in Python.
-   Frontend is implemented in React + TypeScript.
-   All APIs are RBAC-aware.
