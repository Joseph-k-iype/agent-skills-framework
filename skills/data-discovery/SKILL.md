---
name: data-discovery
version: 0.1.0
description: >
  Discovers and catalogs data assets across configured sources.
  Crawls schemas (tables, views, columns, types), profiles basic
  statistics (row counts, null ratios, distinct values), and
  publishes metadata to a catalog endpoint.
runtime: python
api_version: 1
entry: src/main.py
triggers:
  events:
    - data.source.connected
    - schedule.crawl.daily
  commands:
    - /discover
    - /profile
capabilities:
  - catalog:discover
  - catalog:profile
  - catalog:list-sources
config:
  required:
    - sources
    - catalog_endpoint
dependencies:
  pip:
    - pydantic>=2.0
    - sqlalchemy>=2.0
    - pyarrow>=14.0
  skills: []
permissions:
  - resource: datasource
    actions: [read, list]
  - resource: catalog
    actions: [write, create]
---

# Data Discovery

Agent for discovering and cataloging data assets across configured sources.

## Overview

The Data Discovery skill crawls database schemas (tables, views, columns, types), profiles basic statistics (row counts, null ratios, distinct values), and publishes metadata to a catalog endpoint.

## Triggers

Responds to `data.source.connected` and `schedule.crawl.daily` events. Supports `/discover` and `/profile` commands.

## Configuration

Requires `sources` (list of data source connections) and `catalog_endpoint` (URL for publishing discovered metadata).

## Examples

```yaml
# Example trigger via command
/discover
```
