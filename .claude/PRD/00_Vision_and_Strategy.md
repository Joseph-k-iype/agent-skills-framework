# 00_Vision_and_Strategy.md

# Enterprise AI Knowledge & Skills Operating System (EAKSO)

## Technology Principles

-   **Knowledge Layer:** Google Open Knowledge Format (OKF)
-   **Knowledge Graph:** FalkorDB
-   **Semantic Search:** FalkorDB native vector embeddings and graph
    traversal
-   **LLM Gateway:** OpenRouter
-   **Frontend:** React + Vite + TypeScript + Ant Design
-   **Backend:** FastAPI + PostgreSQL + Redis + Celery

------------------------------------------------------------------------

# Core Architecture

``` text
Enterprise Knowledge (OKF)
            │
            ▼
OKF Ingestion Pipeline
            │
            ▼
FalkorDB Knowledge Graph
    • Nodes
    • Relationships
    • Native Embeddings
    • Vector Indexes
            │
            ▼
Hybrid Retrieval
(Graph Traversal + Semantic Search)
            │
            ▼
Knowledge Retrieval Layer
            │
            ▼
Skills
            │
            ▼
Workflows
            │
            ▼
Agents
            │
            ▼
Business Execution
            │
            ▼
Evaluations
            │
            ▼
Knowledge Graph Updates
```

------------------------------------------------------------------------

# Semantic Search Strategy

The platform **does not use a separate vector database**.

FalkorDB is the single source of truth for:

-   Knowledge Graph
-   Relationships
-   Native Vector Embeddings
-   Semantic Similarity
-   Graph Traversal
-   Hybrid Retrieval

Every OKF document, Skill, Capability, Workflow and other searchable
entity stores its embedding directly on the corresponding FalkorDB node.

Search pipeline:

1.  User submits natural language query.
2.  Query embedding is generated.
3.  FalkorDB performs vector similarity search over node embeddings.
4.  Matching nodes are expanded using graph traversal.
5.  Related concepts, dependencies, lineage and capabilities are ranked.
6.  Final results are returned with graph context and explanations.

This avoids maintaining a separate vector store while keeping semantic
retrieval tightly coupled with the enterprise knowledge graph.

------------------------------------------------------------------------

# Knowledge Graph Strategy

FalkorDB is the authoritative platform database.

It stores:

-   OKF Knowledge
-   Skills
-   Workflows
-   Agents
-   Executions
-   Evaluations
-   Organizations
-   Users
-   Capabilities
-   Categories
-   Native Embeddings
-   Semantic Relationships

The graph powers:

-   Semantic Search
-   Recommendation Engine
-   Impact Analysis
-   Duplicate Detection
-   Dependency Discovery
-   Skill Composition
-   Lineage
-   Explainable Retrieval

------------------------------------------------------------------------

# Knowledge vs Skills

Enterprise knowledge remains in OKF.

Skills never duplicate business knowledge.

Skills reference OKF concepts stored in FalkorDB and retrieve context
through graph traversal and semantic search at execution time.

This separation keeps knowledge authoritative while allowing Skills to
evolve independently.

------------------------------------------------------------------------

# Long-Term Vision

The platform establishes:

-   OKF as the enterprise knowledge representation.
-   FalkorDB as the unified semantic knowledge platform.
-   Native graph embeddings as the foundation for intelligent retrieval.
-   Skills as reusable execution assets.
-   Agents that continuously learn from and contribute back to
    enterprise knowledge.
