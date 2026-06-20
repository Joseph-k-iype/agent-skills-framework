---
name: data-lineage
version: 0.1.0
description: >
  Tracks column-level data lineage across pipelines, ETL jobs,
  and data sources. Constructs lineage graphs from metadata,
  parses SQL transformations, and traces data flow from source
  to consumption.
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

Agent for tracking column-level data lineage across pipelines and ETL jobs.

## Overview

The Data Lineage skill constructs lineage graphs from metadata, parses SQL transformations, and traces data flow from source to consumption. Depends on data-discovery for schema metadata.

## Triggers

Responds to `pipeline.completed` and `schema.changed` events. Supports `/trace`, `/lineage-graph`, and `/impact-analysis` commands.

## Configuration

Requires `pipeline_endpoint` and `lineage_store` for storing and retrieving lineage metadata.
