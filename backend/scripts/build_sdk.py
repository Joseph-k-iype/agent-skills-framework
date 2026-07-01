"""Build the eakso SDK wheel + sdist into sdk/python/dist/.

Usage (from repo root or backend/):
    uv run --python 3.12 python backend/scripts/build_sdk.py

Or via uv build directly:
    cd sdk/python && uv build
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def find_repo_root() -> Path:
    """Walk upward from this file until we find a directory containing sdk/ and backend/."""
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "backend").is_dir() and (parent / "sdk").is_dir():
            return parent
    raise RuntimeError("Could not locate repo root (expected sdk/ and backend/ siblings)")


def main() -> None:
    repo_root = find_repo_root()
    sdk_dir = repo_root / "sdk" / "python"

    if not sdk_dir.is_dir():
        print(f"ERROR: SDK source not found at {sdk_dir}", file=sys.stderr)
        sys.exit(1)

    dist_dir = sdk_dir / "dist"
    dist_dir.mkdir(parents=True, exist_ok=True)

    print(f"Building SDK in {sdk_dir} → {dist_dir}")

    result = subprocess.run(
        ["uv", "build", "--out-dir", str(dist_dir)],
        cwd=str(sdk_dir),
        check=False,
    )

    if result.returncode != 0:
        print("ERROR: uv build failed. Trying python -m build as fallback…", file=sys.stderr)
        result = subprocess.run(
            [sys.executable, "-m", "build", "--outdir", str(dist_dir)],
            cwd=str(sdk_dir),
            check=False,
        )

    if result.returncode != 0:
        print("ERROR: SDK build failed.", file=sys.stderr)
        sys.exit(1)

    artifacts = list(dist_dir.iterdir())
    print(f"Build complete. Artifacts ({len(artifacts)}):")
    for a in sorted(artifacts):
        print(f"  {a.name}")


if __name__ == "__main__":
    main()
