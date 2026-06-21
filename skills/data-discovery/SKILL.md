---
name: data-discovery
version: 0.1.0
description: >
  Discovers and catalogs data assets across configured sources: crawls
  schemas (tables, views, columns, types), profiles basic statistics (row
  counts, null ratios, distinct values), and publishes metadata to a catalog
  endpoint. Use this skill when a new data source connects, on the daily
  crawl schedule, or whenever another skill (enrichment, lineage, masking,
  tagging) or a user needs an up-to-date inventory of what tables/columns
  exist before acting on them.
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

Use this skill whenever an agent needs to know what data actually exists in
a connected source. Enrichment, lineage tracing, masking, and tagging all
depend on this skill's catalog output as their starting point — run this
first if no catalog exists yet for a source.

## When to invoke

- A `data.source.connected` event fires (a new source was just configured).
- The daily `schedule.crawl.daily` trigger fires.
- A user or another skill asks "what tables/columns are in `<source>`?" or
  "refresh the catalog for `<source>`".

## What it does, step by step

1. **`/discover`** — for every source in the `sources` config, crawl its
   schema (tables, columns, types), compute basic profile stats (row counts,
   null ratios, distinct counts), and publish the combined result to
   `catalog_endpoint`. Returns `sources_crawled` and `assets_discovered`.
2. **`/profile`** — re-profile the already-configured sources without a
   full schema crawl. Returns `sources_profiled`.
3. **`data.source.connected` event** — crawls only the single source named
   in the event's `payload.source`, and publishes it immediately so a newly
   connected source doesn't have to wait for the daily schedule.

## Configuration

- `sources` — list of `{name, type, connection_string}` data source
  connections to crawl.
- `catalog_endpoint` — URL the discovered metadata is published to.

## Example

```yaml
# Crawl every configured source right now
/discover
```
