---
name: data-quality
version: 0.1.0
description: 'Validates, monitors, and reports on data quality dimensions including
  completeness, consistency, timeliness, uniqueness, and accuracy. Runs configurable
  rule sets against data sources and publishes quality scores.

  '
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
  actions:
  - read
- resource: quality_report
  actions:
  - read
  - write
id: skill://sha256/0176df14469c9c95dd7ed6e846528d54da2ce2621346619b814dab362d8d6553/data-quality@0.1.0
---

# Data Quality

Agent for validating, monitoring, and reporting on data quality dimensions.

## Overview

The Data Quality skill runs configurable rule sets against data sources, measuring completeness, consistency, timeliness, uniqueness, and accuracy. Publishes quality scores to configured endpoints.

## Triggers

Responds to `schedule.quality.daily` and `data.source.updated` events. Supports `/validate`, `/report`, and `/rules` commands.

## Configuration

Requires `quality_rules` (rule definitions) and `report_endpoint` for publishing quality reports.
