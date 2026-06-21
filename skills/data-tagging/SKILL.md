---
name: data-tagging
version: 0.1.0
description: >
  Applies business and technical tags to data assets based on configurable
  rules, with automatic tag propagation through column-level lineage and
  inheritance from upstream assets. Use this skill when an asset is tagged
  (`asset.tagged`) and tags need to propagate downstream, after a schema
  change (`schema.updated`) that may invalidate existing tags, or whenever a
  user or skill needs an asset tagged or its current tag rules listed.
runtime: python
api_version: 1
entry: src/main.py
triggers:
  events:
    - asset.tagged
    - schema.updated
  commands:
    - /apply-tags
    - /propagate
    - /list-tags
capabilities:
  - tagging:apply
  - tagging:propagate
  - tagging:list
config:
  required:
    - tag_rules
    - tag_endpoint
dependencies:
  pip:
    - pydantic>=2.0
    - pyyaml>=6.0
  skills:
    - data-lineage@^0.1.0
permissions:
  - resource: tag
    actions: [read, write, delete]
  - resource: asset
    actions: [read, write]
---

# Data Tagging

Use this skill to keep business/technical tags consistent across assets —
apply tags from configured rules and propagate them through lineage so
downstream assets inherit upstream classifications automatically.

## When to invoke

- An asset was just tagged (`asset.tagged`) — propagate those tags to
  related assets through lineage.
- A schema changed (`schema.updated`) — re-resolve and re-propagate tags,
  since a schema change can invalidate previously-matched rules.
- A user or another skill needs tags applied to a batch of assets, tags
  propagated from a specific asset, or the current tag rules listed.

## What it does, step by step

1. **`/apply-tags`** — given a list of `assets`, matches each against every
   configured `tag_rules` entry and returns how many assets were tagged and
   how many total tags were applied.
2. **`/propagate`** — given an `asset_id` and a list of `tags`, propagates
   those tags downstream and reports how many were propagated.
3. **`/list-tags`** — lists the currently configured tagging rules.
4. **`asset.tagged` event** — resolves and propagates tags for the asset
   named in `payload.asset`.
5. **`schema.updated` event** — re-resolves and re-propagates tags for the
   asset named in `payload.asset` after its schema changes.

## Configuration

- `tag_rules` — YAML-based rule definitions (column type or name pattern →
  tag) matched against each asset.
- `tag_endpoint` — where tag assignments are persisted.

## Dependencies

Depends on `data-lineage` for the lineage relationships tag propagation
walks through.
