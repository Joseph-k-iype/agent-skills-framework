---
name: data-lineage
version: 0.1.0
description: >
  Tracks column-level data lineage across pipelines, ETL jobs, and data
  sources, constructing lineage graphs from metadata and tracing data flow
  from source to consumption. Use this skill right after an ETL pipeline
  finishes (`pipeline.completed`), when a source schema changes
  (`schema.changed`) and you need to know what breaks downstream, or
  whenever a user or skill needs to trace a column's origin or assess the
  blast radius of a change before making it.
runtime: python
api_version: 1
entry: src/main.py
triggers:
  events:
    - pipeline.completed
    - schema.changed
  commands:
    - /trace
    - /lineage-graph
    - /impact-analysis
capabilities:
  - lineage:trace
  - lineage:graph
  - lineage:impact
config:
  required:
    - pipeline_endpoint
    - lineage_store
dependencies:
  pip:
    - pydantic>=2.0
    - sqlparse>=0.4
    - networkx>=3.0
  skills:
    - data-discovery@^0.1.0
permissions:
  - resource: lineage
    actions: [read, write]
  - resource: pipeline
    actions: [read]
  - resource: datasource
    actions: [read]
---

# Data Lineage

Use this skill to answer "where did this column come from?" and "what
breaks if I change this table?" — it builds and queries a lineage graph over
the assets `data-discovery` has cataloged.

## When to invoke

- An ETL pipeline just finished (`pipeline.completed`) — trace lineage for
  the tables it touched while the run is still fresh context.
- A source schema changed (`schema.changed`) — re-run impact analysis to
  catch anything downstream before it breaks silently.
- A user or another skill needs to trace a column's upstream origin, build a
  full lineage graph for a table, or assess the blast radius of a proposed
  change.

## What it does, step by step

1. **`/trace`** — given a `table` and `column`, returns the upstream
   lineage chain showing every hop the column passed through.
2. **`/lineage-graph`** — given a `table`, returns the full lineage graph
   (nodes and edges) for that table, suitable for visualization.
3. **`/impact-analysis`** — given a `table`, reports which downstream
   assets (tables, reports, dashboards) would be affected by a change to it.
4. **`pipeline.completed` event** — traces lineage for every table named in
   `payload.tables`, right after the pipeline that produced them finishes.
5. **`schema.changed` event** — re-runs `/impact-analysis` for the table
   named in `payload.table`, so consumers learn about a breaking schema
   change before they hit it.

## Configuration

- `pipeline_endpoint` — source of pipeline run metadata used to build
  lineage chains.
- `lineage_store` — where computed lineage graphs are persisted/retrieved.

## Dependencies

Depends on `data-discovery` for the schema metadata that lineage tracing is
built on.
