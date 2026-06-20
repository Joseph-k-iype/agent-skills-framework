---
name: data-masking
version: 0.1.0
description: 'Applies PII and PHI masking policies to sensitive data fields. Supports
  multiple masking techniques including redaction, tokenization, encryption, and format-preserving
  masking. Integrates with data-discovery to detect sensitive columns.

  '
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
  actions:
  - read
  - execute
- resource: masking_policy
  actions:
  - read
  - write
- resource: audit_log
  actions:
  - write
id: skill://sha256/c3ee784ca225dc889023f8648c62dcd8748f8ab018742ca47d757381ae005c2e/data-masking@0.1.0
---

# Data Masking

Agent for applying PII and PHI masking policies to sensitive data fields.

## Overview

The Data Masking skill supports redaction, tokenization, encryption, and format-preserving masking. Integrates with data-discovery and data-tagging for sensitive column detection.

## Triggers

Responds to `policy.updated` and `asset.classified` events. Supports `/mask`, `/policies`, and `/discover-sensitive` commands.

## Configuration

Requires `masking_policies` (policy definitions) and `pii_endpoint` for PII data management.
