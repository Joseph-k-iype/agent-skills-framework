---
name: data-masking
version: 0.1.0
description: >
  Applies PII and PHI masking policies to sensitive data fields, supporting
  redaction, tokenization, encryption, and format-preserving masking. Use
  this skill when an asset is classified as PII/PHI (`asset.classified`),
  when a masking policy changes (`policy.updated`), or whenever a user or
  skill needs sensitive columns identified or a dataset masked before it's
  shared or queried.
runtime: python
api_version: 1
entry: src/main.py
triggers:
  events:
    - policy.updated
    - asset.classified
  commands:
    - /mask
    - /policies
    - /discover-sensitive
capabilities:
  - masking:apply
  - masking:policies
  - masking:discover
config:
  required:
    - masking_policies
    - pii_endpoint
dependencies:
  pip:
    - pydantic>=2.0
    - cryptography>=41.0
  skills:
    - data-discovery@^0.1.0
    - data-tagging@^0.1.0
permissions:
  - resource: pii_data
    actions: [read, execute]
  - resource: masking_policy
    actions: [read, write]
  - resource: audit_log
    actions: [write]
---

# Data Masking

Use this skill to keep PII/PHI out of places it shouldn't be — find
sensitive columns and apply a masking policy before a dataset is shared,
exported, or queried by something that shouldn't see raw values.

## When to invoke

- An asset was just classified as PII or PHI (`asset.classified`) — decide
  whether masking is required before anyone reads it.
- A masking policy changed (`policy.updated`) — apply the new policy going
  forward.
- A user or another skill needs sensitive columns identified in a schema, or
  needs a dataset masked according to a named policy.

## What it does, step by step

1. **`/discover-sensitive`** — given a `schema` (list of columns), flags
   every column whose name matches a known PII pattern (email, ssn, phone,
   address, credit card, password, etc.).
2. **`/mask`** — given a `dataset` and a `policy` name, applies the
   policy's masking technique (default: redact) to the fields it covers.
3. **`/policies`** — lists the currently configured masking policies.
4. **`asset.classified` event** — when `payload.classification` is `pii`
   or `phi`, reports whether the named asset requires masking.
5. **`policy.updated` event** — appends the new policy and reports how many
   policies are now configured.

## Configuration

- `masking_policies` — named policy definitions (technique + covered
  fields).
- `pii_endpoint` — service used for PII pattern/classification lookups.

## Dependencies

Integrates with `data-discovery` (schema metadata) and `data-tagging`
(classification signals) to decide what needs masking.
