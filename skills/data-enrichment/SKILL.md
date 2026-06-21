---
name: data-enrichment
version: 0.1.0
description: >
  Augments cataloged data assets with classifications, confidence scores,
  and business glossary terms by matching them against configured
  enrichment rules. Use this skill right after data-discovery finds a new
  asset (on the `asset.discovered` event), after the business glossary
  changes, or whenever a user or skill needs an asset's business meaning
  (classification, glossary terms) rather than just its raw schema.
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
    actions: [read, write]
  - resource: glossary
    actions: [read]
  - resource: classification
    actions: [write]
---

# Data Enrichment

Use this skill to turn a raw cataloged asset (from `data-discovery`) into
something with business meaning — a classification, a confidence score, and
business glossary terms — so downstream consumers don't have to guess what a
table or column actually represents.

## When to invoke

- A `data.discovery` run just published a new asset (`asset.discovered`
  event) — enrich it before anyone queries it.
- The business glossary changed (`glossary.updated`) — re-link terms.
- A user or another skill needs an asset's business classification/glossary
  terms, not just its column names and types.

## What it does, step by step

1. **`/enrich`** — given a list of `assets` (each `{id, name, ...}`), match
   each one against every configured `enrichment_rules` entry; an asset gets
   a classification (with a confidence score) for every rule whose pattern
   matches, then is linked to relevant glossary terms. Returns one result
   per input asset.
2. **`/link-glossary`** — reports the configured `glossary_endpoint` used
   for term resolution.
3. **`asset.discovered` event** — runs the same classify-and-link flow for
   the single asset named in `payload.asset`, immediately after discovery.

## Configuration

- `enrichment_rules` — list of `{pattern, classification, confidence}` rules
  matched against each asset.
- `glossary_endpoint` — URL of the business glossary used for term linking.

## Dependencies

Depends on `data-discovery` (assets to enrich) and `data-lineage` (lineage
context for inferring relationships between assets).
