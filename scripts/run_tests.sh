#!/usr/bin/env bash
# Run every test suite in the monorepo. Each Python package is imported from a
# different root, so each runs in its own cwd with PYTHONPATH pointed at the SDK.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SDK="$ROOT/sdks/python"
PY="${PYTHON:-}"
if [ -z "$PY" ]; then
  if command -v python3 >/dev/null 2>&1; then PY=python3; else PY=python; fi
fi
fail=0

run() {
  local label="$1"; shift
  echo "==> $label"
  if "$@"; then
    echo "    PASS: $label"
  else
    echo "    FAIL: $label"
    fail=1
  fi
}

# Python SDK (skill_sdk importable from its own dir)
run "python-sdk" bash -c "cd '$SDK' && '$PY' -m pytest -q"

# CLI (imports cli.src.main from repo root; needs skill_sdk on path)
run "cli" bash -c "cd '$ROOT' && PYTHONPATH='$SDK' '$PY' -m pytest cli/tests -q"

# Reference skill
run "skill:data-discovery" bash -c "cd '$ROOT/skills/data-discovery' && PYTHONPATH='$SDK' '$PY' -m pytest -q"

# Test harness
run "harness" bash -c "cd '$ROOT/testing' && PYTHONPATH='$SDK' '$PY' -m pytest -q"

# TypeScript SDK (skip gracefully if deps aren't installed)
if command -v npm >/dev/null 2>&1; then
  if [ -d "$ROOT/sdks/typescript/node_modules" ]; then
    run "typescript-sdk" bash -c "cd '$ROOT/sdks/typescript' && npm test --silent"
  else
    echo "==> typescript-sdk (skipped: run 'npm install' in sdks/typescript first)"
  fi
else
  echo "==> typescript-sdk (skipped: npm not found)"
fi

if [ "$fail" -ne 0 ]; then
  echo "SOME SUITES FAILED"
  exit 1
fi
echo "ALL SUITES PASSED"
