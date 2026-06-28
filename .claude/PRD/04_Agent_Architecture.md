# 04_Agent_Architecture.md (Expanded)

> **Status:** Expanded Draft (v1.2)

## Note

The previous version focused too heavily on OKF. This document expands
the **complete agent ecosystem**. The Knowledge Graph and OKF
specification will still be described in detail in
**05_Knowledge_Graph_and_OKF.md**.

------------------------------------------------------------------------

# Agentic Architecture

The platform follows a **Supervisor → Specialist** architecture
implemented with **LangGraph**.

                    User
                      │
              FastAPI Gateway
                      │
              LangGraph Supervisor
                      │
       ┌──────────────┼─────────────────────────────┐
       │              │             │               │
    Authoring     Knowledge     Execution     Governance
    Agents         Agents         Agents         Agents
                      │
                 FalkorDB
                      │
             OKF Knowledge Base
                      │
                 OpenRouter

The Supervisor is responsible for: - Intent classification - Agent
routing - State management - Human approval routing - Retry policies -
Event publication - Final response assembly

No specialist agent communicates directly with another specialist. All
coordination happens through the Supervisor.

------------------------------------------------------------------------

# Shared Agent Contract

Every agent defines:

-   Purpose
-   Inputs
-   Outputs
-   Tools
-   Graph Access
-   Events Consumed
-   Events Produced
-   Failure Strategy
-   Human Approval Requirement

------------------------------------------------------------------------

# 1. Knowledge Retrieval Agent

Purpose: Retrieve authoritative enterprise knowledge.

Tools: - FalkorDB Vector Search - Graph Traversal - Cypher Queries

Inputs: - User Query - Workspace - Current Asset

Outputs: - Ranked Context - Supporting Documents - Graph Paths -
Citations

------------------------------------------------------------------------

# 2. OKF Agent

Purpose: Synchronize enterprise knowledge into the graph.

Responsibilities: - Parse Markdown - Validate YAML - Resolve links -
Detect orphan documents - Update FalkorDB - Maintain lineage - Detect
duplicate concepts

------------------------------------------------------------------------

# 3. Workspace Agent

Purpose: Maintain hierarchical workspace.

Responsibilities: - Folder creation - Folder move - Folder delete -
Permission inheritance - Version tracking - Synchronize hierarchy with
FalkorDB

Events: FolderCreated FolderMoved FolderDeleted

------------------------------------------------------------------------

# 4. Skill Authoring Agent

Purpose: Assist developers during skill creation.

Responsibilities: - Generate metadata - Recommend capability tags -
Suggest folder placement - Link relevant OKF documents - Recommend
existing reusable skills - Generate documentation skeleton - Generate
examples - Detect missing dependencies

Requires human approval before publish.

------------------------------------------------------------------------

# 5. Workflow Authoring Agent

Purpose: Generate executable workflows.

Responsibilities: - Create workflow graph - Reuse existing skills -
Detect cycles - Validate inputs/outputs - Recommend reusable
sub-workflows - Export React Flow JSON

------------------------------------------------------------------------

# 6. Knowledge Graph Agent

Purpose: Maintain graph quality.

Responsibilities: - Create nodes - Create relationships - Merge
duplicates - Remove stale relationships - Update embeddings - Validate
graph integrity - Maintain lineage

------------------------------------------------------------------------

# 7. Search Agent

Pipeline

Intent → Vector Search → Graph Expansion → Re-ranking → Explainability →
Results

Returns: Skills Folders Workflows OKF Documents Agents Related Assets

------------------------------------------------------------------------

# 8. Evaluator Supervisor

Coordinates six evaluator agents.

## Security Evaluator

Checks secrets, unsafe prompts, permissions.

## Performance Evaluator

Latency, complexity, scalability.

## Quality Evaluator

Correctness and completeness.

## Documentation Evaluator

OKF references, documentation quality.

## Cost Evaluator

Estimated OpenRouter token cost.

## Governance Evaluator

Enterprise compliance.

Supervisor aggregates:

-   Overall Score
-   Confidence
-   Evidence
-   Recommendations
-   Blocking Issues

------------------------------------------------------------------------

# 9. Governance Agent

Purpose: Enforce enterprise standards.

Responsibilities: - Naming conventions - Folder structure - Metadata
completeness - Policy compliance - License validation - RBAC
validation - Approval routing

Can block publication.

------------------------------------------------------------------------

# 10. Marketplace Agent

Responsibilities: - Publish public assets - Create listings - Calculate
rankings - Trending - Featured collections - Spam detection - Duplicate
detection

Never exposes private assets.

------------------------------------------------------------------------

# 11. Execution Agent

Purpose: Execute workflows.

Responsibilities: - Resolve dependencies - Retrieve knowledge - Invoke
OpenRouter - Execute graph - Capture telemetry - Persist execution
history - Update FalkorDB

------------------------------------------------------------------------

# 12. Recommendation Agent

Signals used:

-   Graph proximity
-   Embeddings
-   Usage frequency
-   Folder context
-   Evaluations
-   Similarity
-   Dependency graph

Recommendations: - Related skills - Missing skills - Better workflows -
Alternative implementations

------------------------------------------------------------------------

# 13. Documentation Agent

Purpose: Maintain documentation quality.

Responsibilities: - Generate drafts - Update examples - Produce
changelog - Summarize changes - Validate Markdown - Check OKF links

------------------------------------------------------------------------

# 14. Notification Agent

Publishes:

-   Review requested
-   Evaluation complete
-   Workflow failed
-   Skill published
-   Mention
-   Approval required

------------------------------------------------------------------------

# 15. Analytics Agent

Produces:

-   Usage metrics
-   Adoption
-   Skill reuse
-   Evaluation trends
-   Graph growth
-   Workspace insights

------------------------------------------------------------------------

# End-to-End Flow

    Developer
       │
    Skill Authoring Agent
       │
    Knowledge Retrieval Agent
       │
    Workflow Agent
       │
    Knowledge Graph Agent
       │
    Evaluator Supervisor
       │
    Governance Agent
       │
    Marketplace Agent
       │
    Notification Agent

------------------------------------------------------------------------

# Acceptance Criteria

-   All agents implement the shared contract.
-   Supervisor owns orchestration.
-   Knowledge Retrieval precedes any LLM reasoning.
-   Every agent publishes domain events.
-   Every graph mutation is persisted in FalkorDB.
-   Agents are independently deployable and testable.
