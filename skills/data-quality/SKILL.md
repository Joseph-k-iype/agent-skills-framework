---
name: data-quality
version: 0.1.0
description: >
  Validates, monitors, and reports on data quality dimensions including
  completeness, consistency, timeliness, uniqueness, and accuracy by running
  configurable rule sets against data sources. Use this skill on the daily
  quality schedule (`schedule.quality.daily`), right after a source updates
  (`data.source.updated`), or whenever a user or skill needs a source's
  current quality score or a published quality report before relying on its
  data.
runtime: python
api_version: 1
entry: src/main.py
triggers:
  events:
    - schedule.quality.daily
    - data.source.updated
  commands:
    - /validate
    - /report
    - /rules
capabilities:
  - quality:validate
  - quality:report
  - quality:rules
config:
  required:
    - quality_rules
    - report_endpoint
dependencies:
  pip:
    - pydantic>=2.0
    - pandas>=2.0
    - sqlalchemy>=2.0
  skills: []
permissions:
  - resource: datasource
    actions: [read]
  - resource: quality_report
    actions: [read, write]
---

# Data Quality

Use this skill to answer "can I trust this data?" — it runs configurable
quality rules against sources and scores them across completeness,
consistency, timeliness, uniqueness, and accuracy.

## When to invoke

- The daily quality schedule fires (`schedule.quality.daily`) — check every
  configured source and report which ones are passing.
- A source was just updated (`data.source.updated`) — re-validate just that
  source rather than waiting for the next scheduled run.
- A user or another skill needs a source's current quality score, a list of
  configured rules, or a published quality report.

## What it does, step by step

1. **`/validate`** — given a list of `sources`, runs the configured
   `quality_rules` against each and returns a per-source result.
2. **`/report`** — runs the same checks as `/validate` but also publishes
   the results to `report_endpoint`, returning how many sources were
   reported.
3. **`/rules`** — lists the currently configured quality rules.
4. **`schedule.quality.daily` event** — runs `/validate` across every source
   named in `payload.sources` and reports how many are passing.
5. **`data.source.updated` event** — re-runs quality checks for just the
   source named in `payload.source`.

## Configuration

- `quality_rules` — rule definitions (dimension, threshold) checked against
  each source.
- `report_endpoint` — where published quality reports are sent.
