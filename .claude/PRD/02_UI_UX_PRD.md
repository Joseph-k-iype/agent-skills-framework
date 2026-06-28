# 02_UI_UX_PRD.md

# UI / UX Product Requirements Document

Version: 1.0

## Purpose

Define the complete user experience for the Enterprise AI Knowledge &
Skills Operating System (EAKSO). This document specifies layouts,
navigation, design system, page contracts and interaction patterns for
implementation.

------------------------------------------------------------------------

# Design Principles

-   Swiss Design inspired
-   White theme only
-   Tesla Red (#E82127) accent
-   Minimal borders
-   High information density
-   Large whitespace
-   Typography first
-   Accessibility (WCAG AA)
-   Responsive desktop-first

------------------------------------------------------------------------

# Design System

## Framework

-   Ant Design
-   React + TypeScript
-   Vite

## Grid

-   8px spacing system
-   12-column responsive grid
-   Max content width: 1440px

## Typography

-   Clear hierarchy
-   Large page titles
-   Minimal decorative elements

## Colors

Primary: Tesla Red (#E82127)

Neutral palette: - White background - Light gray surfaces - Dark gray
text

No gradients. No dark mode.

------------------------------------------------------------------------

# Global Application Shell

## Consumer

Layout

Top Navigation │ ├── Logo ├── Marketplace ├── Collections ├── Categories
├── Search ├── Notifications └── Profile

No sidebar.

Landing page resembles a modern software marketplace.

------------------------------------------------------------------------

## Developer

Layout

Header + Left Sidebar + Content Area

Sidebar

-   Dashboard
-   Workspace
-   Workflow Builder
-   Knowledge Graph
-   Evaluator
-   Executions
-   Analytics
-   Community

------------------------------------------------------------------------

## Admin

Same layout as Developer.

Additional sidebar entries

-   Users
-   Roles
-   Organizations
-   Marketplace Moderation
-   Categories
-   Capabilities
-   Taxonomies
-   Audit Logs
-   System Health
-   Settings

------------------------------------------------------------------------

# Global Components

Every layout includes:

-   Global semantic search
-   Breadcrumbs
-   Notification center
-   User profile menu
-   Command palette (Ctrl/Cmd + K)
-   Loading skeletons
-   Toast notifications

------------------------------------------------------------------------

# Workspace Experience

The Workspace is the primary authoring interface.

Display as an expandable tree.

Workspace ├── Knowledge Package │ ├── Folder │ ├── Folder │ └── Folder
└── Knowledge Package

Each node supports:

-   Expand / Collapse
-   Right-click context menu
-   Drag & Drop
-   Rename
-   Move
-   Duplicate
-   Delete
-   Version History
-   Permissions
-   Favorite

------------------------------------------------------------------------

# Page Contract Template

Every page must define:

-   Purpose
-   Route
-   Allowed Roles
-   Layout
-   Components
-   Primary Actions
-   Secondary Actions
-   API Dependencies
-   Loading State
-   Empty State
-   Error State
-   Acceptance Criteria

------------------------------------------------------------------------

# Core Pages

## Dashboard

Widgets

-   My Workspace
-   Recent Activity
-   Pending Evaluations
-   Recent Executions
-   Graph Insights
-   Quick Actions

Quick Actions

-   Create Skill
-   Create Workflow
-   Create Folder
-   Import OKF

------------------------------------------------------------------------

## Marketplace

Purpose

Discover reusable Skills.

Sections

-   Hero Search
-   Featured
-   Trending
-   Verified
-   New Releases
-   Collections
-   Categories

Skill Cards

-   Name
-   Summary
-   Author
-   Rating
-   Downloads
-   Version
-   Tags

Actions

-   View
-   Clone to Workspace

------------------------------------------------------------------------

## Workspace

Split layout

Left

Folder Tree

Right

Selected Asset Details

Toolbar

-   New Folder
-   New Skill
-   New Workflow
-   Import OKF
-   Search
-   Filter

------------------------------------------------------------------------

## Skill Editor

Tabbed interface

-   Overview
-   Metadata
-   OKF References
-   Workflow
-   Runtime
-   Capabilities
-   Evaluation
-   Versions

Sticky action bar

-   Save Draft
-   Validate
-   Publish

------------------------------------------------------------------------

## Workflow Builder

React Flow canvas

Panels

-   Node Library
-   Properties
-   Validation
-   Execution Preview

Toolbar

-   Auto Layout
-   Validate
-   Run
-   Save
-   Publish

------------------------------------------------------------------------

## Knowledge Graph

Two modes

Explorer Mode

Displays Workspace hierarchy.

Relationship Mode

Displays graph relationships for selected node.

Toolbar

-   Semantic Search
-   Expand
-   Collapse
-   Fit View
-   Filter Relationships
-   Export

------------------------------------------------------------------------

## Evaluator

Views

-   Queue
-   Reports
-   Recommendations
-   History

Report cards include

-   Security
-   Performance
-   Documentation
-   Cost
-   Compliance
-   Overall Score

------------------------------------------------------------------------

## Analytics

Sections

-   Usage
-   Skill Adoption
-   Knowledge Growth
-   Graph Metrics
-   Evaluation Trends
-   Execution Trends

------------------------------------------------------------------------

## Administration

Cards

-   Users
-   LDAP Groups
-   Roles
-   Permissions
-   Categories
-   Capabilities
-   Taxonomies
-   Audit Logs
-   Health

------------------------------------------------------------------------

# Interaction Guidelines

-   Double-click opens editor
-   Right-click opens context menu
-   Drag & Drop reorders folders
-   Keyboard shortcuts available
-   Optimistic UI updates
-   Infinite scrolling where applicable

------------------------------------------------------------------------

# Empty States

Every empty state must include:

-   Explanation
-   Primary CTA
-   Secondary help link

------------------------------------------------------------------------

# Error States

Display:

-   Human-readable error
-   Technical error ID
-   Retry action
-   Support link

------------------------------------------------------------------------

# Acceptance Criteria

-   Marketplace and Workspace are distinct experiences.
-   Navigation adapts based on RBAC.
-   Workspace mirrors the OKF directory hierarchy.
-   React Flow powers Workflow Builder and Knowledge Graph.
-   Ant Design components are used consistently.
-   All interactions are keyboard accessible.
-   Every page follows the defined page contract.
