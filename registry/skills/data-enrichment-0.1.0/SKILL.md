---
name: data-enrichment
version: 0.1.0
description: 'Augments data assets with business lineage, glossary terms, and classifications.
  Enriches assets by resolving foreign keys, inferring semantic types, and linking
  to business metadata repositories.

  '
runtime: python
api_version: 1
entry: src/main.py
triggers:
  events:
  - asset.discovered
  - glossary.updated
  commands:
  - /enrich
  - /classify
  - /link-glossary
capabilities:
- enrichment:apply
- enrichment:classify
- enrichment:glossary
config:
  required:
  - enrichment_rules
  - glossary_endpoint
dependencies:
  pip:
  - pydantic>=2.0
  - sqlalchemy>=2.0
  skills:
  - data-discovery@^0.1.0
  - data-lineage@^0.1.0
permissions:
- resource: asset
  actions:
  - read
  - write
- resource: glossary
  actions:
  - read
- resource: classification
  actions:
  - write
id: skill://sha256/6cdccf661706eebdc2526fac096ea1dc98bfebc51338d8e122fc38b9602e9a17/data-enrichment@0.1.0
---

# Data Enrichment

Agent for augmenting data assets with business lineage, glossary terms, and classifications.

## Overview

The Data Enrichment skill enriches assets by resolving foreign keys, inferring semantic types, and linking to business metadata repositories. Depends on data-discovery and data-lineage.

## Triggers

Responds to `asset.discovered` and `glossary.updated` events. Supports `/enrich`, `/classify`, and `/link-glossary` commands.

## Configuration

Requires `enrichment_rules` and `glossary_endpoint` for linking to business metadata.
