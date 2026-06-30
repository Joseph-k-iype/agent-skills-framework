"""Demo marketplace catalog seed.

The storefront (Swiss hero + masonry redesign) needs varied, real-looking
content to render against — not a single test listing or 18 duplicated
"Lineage Tracker" rows left behind by integration tests (see
``scripts/clean_test_listings.py`` for the cleanup side of that problem).

This module inserts ~10 fixed demo skills, each with a single, real
``SkillVersion`` (markdown content with frontmatter, hashed via the same
``content_sha`` used for real publishes) the first time it runs, and is a
no-op on every subsequent run — so it is safe to call unconditionally from
``app.db.seed.seed()`` on every app start / ``python -m app.db.seed``.

Idempotency marker: any row with ``source_workspace_id == DEMO_WORKSPACE_ID``
existing already means the demo catalog has been seeded.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.logging import get_logger
from app.models import MarketplaceListing, SkillVersion
from app.okf.canonical import content_sha

log = get_logger("seed_marketplace")

DEMO_WORKSPACE_ID = "demo"


def _md(frontmatter: dict, body: str) -> tuple[str, str]:
    """Render frontmatter + body into a single markdown document, the way a
    real skill file looks on disk, and return (full_markdown, body)."""
    fm_lines = ["---"]
    for k, v in frontmatter.items():
        if isinstance(v, list):
            items = ", ".join(f'"{i}"' for i in v)
            fm_lines.append(f"{k}: [{items}]")
        else:
            fm_lines.append(f"{k}: {v}")
    fm_lines.append("---")
    full = "\n".join(fm_lines) + "\n\n" + body.strip() + "\n"
    return full, body


# Each entry: (title, type, category, summary, tags, downloads, featured, body).
# author_id is left null: it's a strict FK to users.id and these are demo
# listings with no backing user row, not real authors.
_DEMO_SKILLS: list[dict] = [
    {
        "title": "CSV to Knowledge Graph",
        "type": "skill",
        "category": "Transformation",
        "summary": (
            "Ingests arbitrary CSV exports, infers entity and relationship types from "
            "column headers and value shapes, and emits a normalized property graph "
            "ready to load into Neo4j, FalkorDB, or any RDF-compatible store. Handles "
            "composite keys, self-referential rows, and dirty headers without manual mapping."
        ),
        "tags": ["csv", "graph", "etl"],
        "downloads": 482,
        "featured": True,
        "body": (
            "# CSV to Knowledge Graph\n\n"
            "Turn a flat CSV export into a connected property graph in one pass.\n\n"
            "## How it works\n\n"
            "```mermaid\n"
            "flowchart LR\n"
            "    A[CSV rows] --> B[Header inference]\n"
            "    B --> C[Entity extraction]\n"
            "    C --> D[Relationship detection]\n"
            "    D --> E[(Graph store)]\n"
            "```\n\n"
            "## Steps\n\n"
            "1. Sniff delimiter and encoding.\n"
            "2. Classify each column as an entity attribute, a foreign-key-shaped "
            "reference, or a relationship label.\n"
            "3. Deduplicate entities by composite natural key.\n"
            "4. Emit `CREATE`/`MERGE` Cypher (or RDF triples) for the target store.\n\n"
            "Works well on exports from CRMs, ERPs, and spreadsheet-driven master data."
        ),
    },
    {
        "title": "Entity Resolver",
        "type": "skill",
        "category": "Enrichment",
        "summary": (
            "Matches and merges duplicate customer or organization records across "
            "sources using fuzzy name matching, address normalization, and configurable "
            "blocking keys."
        ),
        "tags": ["dedup", "matching", "mdm"],
        "downloads": 311,
        "featured": False,
        "body": (
            "# Entity Resolver\n\n"
            "Identify and merge duplicate entities across messy, multi-source datasets.\n\n"
            "## Matching strategy\n\n"
            "- Blocking on normalized postal code + first token of name.\n"
            "- Jaro-Winkler similarity on name fields, with a configurable threshold.\n"
            "- Address normalization before comparison (see Address Normalizer).\n\n"
            "Outputs a cluster ID per resolved entity plus a confidence score, so "
            "low-confidence merges can be queued for human review instead of "
            "auto-applied."
        ),
    },
    {
        "title": "Schema Guardrail",
        "type": "agent",
        "category": "Validation",
        "summary": (
            "Validates incoming records against an evolving JSON Schema, flags breaking "
            "changes before they hit production tables, and proposes a migration."
        ),
        "tags": ["schema", "validation"],
        "downloads": 198,
        "featured": False,
        "body": (
            "# Schema Guardrail\n\n"
            "Catch schema drift before it silently corrupts downstream tables.\n\n"
            "## What it checks\n\n"
            "- New required fields without defaults.\n"
            "- Type narrowing (e.g. string -> enum) that would reject existing values.\n"
            "- Removed fields still referenced by active queries.\n\n"
            "Emits a diff-style report and, where safe, a backward-compatible migration."
        ),
    },
    {
        "title": "PII Redactor",
        "type": "prompt",
        "category": "Prompt",
        "summary": (
            "A prompt skill that scans free text for names, emails, phone numbers, and "
            "national ID patterns, then redacts or tokenizes them before the text is sent "
            "to a downstream LLM call."
        ),
        "tags": ["pii", "privacy", "compliance"],
        "downloads": 256,
        "featured": False,
        "body": (
            "# PII Redactor\n\n"
            "Strip personally identifiable information from free text before it leaves "
            "your trust boundary.\n\n"
            "## Detected patterns\n\n"
            "- Full names (NER-based, locale-aware).\n"
            "- Emails, phone numbers, IBANs.\n"
            "- National ID and passport number shapes (configurable per country).\n\n"
            "Replaces matches with stable tokens (`[PERSON_1]`, `[EMAIL_2]`) so "
            "downstream logic can still reason about structure without seeing the "
            "underlying value."
        ),
    },
    {
        "title": "Address Normalizer",
        "type": "skill",
        "category": "Transformation",
        "summary": (
            "Parses and standardizes postal addresses across formats and locales into a "
            "single structured shape (street, number, unit, locality, region, postal "
            "code, country), suitable for deduplication or geocoding."
        ),
        "tags": ["address", "i18n", "etl"],
        "downloads": 167,
        "featured": False,
        "body": (
            "# Address Normalizer\n\n"
            "Standardize free-text postal addresses into structured components.\n\n"
            "## Output shape\n\n"
            "`{ street, house_number, unit, locality, region, postal_code, "
            "country_code }`\n\n"
            "Handles Swiss, German, French, UK, and US conventions out of the box; "
            "other locales fall back to a best-effort tokenizer with a confidence flag."
        ),
    },
    {
        "title": "Anomaly Detector",
        "type": "skill",
        "category": "Validation",
        "summary": (
            "Flags statistical outliers in numeric and time-series columns using robust "
            "z-score and seasonal decomposition, with tunable sensitivity per column."
        ),
        "tags": ["anomaly", "stats"],
        "downloads": 142,
        "featured": False,
        "body": (
            "# Anomaly Detector\n\n"
            "Surface outliers in tabular and time-series data before they reach a "
            "report or a model.\n\n"
            "## Methods\n\n"
            "- Robust z-score (median + MAD) for static numeric columns.\n"
            "- STL seasonal decomposition + residual thresholding for time series.\n\n"
            "Returns a per-row anomaly score, not a hard pass/fail, so callers can set "
            "their own threshold."
        ),
    },
    {
        "title": "Geocoder",
        "type": "skill",
        "category": "Enrichment",
        "summary": (
            "Resolves a normalized address or place name to latitude/longitude and "
            "administrative boundaries, with offline caching for repeat lookups."
        ),
        "tags": ["geo", "enrichment"],
        "downloads": 221,
        "featured": False,
        "body": (
            "# Geocoder\n\n"
            "Resolve addresses and place names to coordinates and administrative "
            "boundaries.\n\n"
            "## Behaviour\n\n"
            "- Prefers an exact match against a local gazetteer cache.\n"
            "- Falls back to a configurable external provider on cache miss.\n"
            "- Caches the result so a repeat lookup on the same normalized address is "
            "free.\n\n"
            "Pair with Address Normalizer for higher cache hit rates."
        ),
    },
    {
        "title": "Currency Converter",
        "type": "workflow",
        "category": "Transformation",
        "summary": (
            "Converts monetary amounts between currencies using daily reference rates, "
            "with explicit handling of the as-of date so historical records stay "
            "reproducible."
        ),
        "tags": ["finance", "etl"],
        "downloads": 95,
        "featured": False,
        "body": (
            "# Currency Converter\n\n"
            "Convert amounts between currencies against daily reference rates.\n\n"
            "## Why an as-of date matters\n\n"
            "Converting a 2019 invoice at today's rate silently corrupts historical "
            "reporting. This skill requires an explicit as-of date and resolves the "
            "nearest published rate on or before it, so the same input always produces "
            "the same output."
        ),
    },
    {
        "title": "Data Cleanup Suite",
        "type": "toolkit",
        "category": "Toolkit",
        "summary": (
            "A bundled toolkit of small, composable cleanup steps — trim whitespace, "
            "normalize casing, coerce types, fill or flag nulls per a declared policy — "
            "for the unglamorous 80% of any data pipeline."
        ),
        "tags": ["cleanup", "etl", "toolkit"],
        "downloads": 389,
        "featured": True,
        "body": (
            "# Data Cleanup Suite\n\n"
            "A toolkit of small, composable cleanup steps for the unglamorous 80% of "
            "any data pipeline.\n\n"
            "## Included steps\n\n"
            "- Whitespace and invisible-character trimming.\n"
            "- Case normalization (configurable per column).\n"
            "- Type coercion with an explicit failure mode (drop / null / raise).\n"
            "- Null handling per a declared policy (default, drop, flag).\n\n"
            "Each step is independently usable; the suite just wires them into a "
            "sensible default pipeline."
        ),
    },
    {
        "title": "Date Parser",
        "type": "skill",
        "category": "Extraction",
        "summary": (
            "Extracts and normalizes dates from free text and ambiguous formats into "
            "ISO 8601, with locale-aware day/month disambiguation."
        ),
        "tags": ["dates", "extraction"],
        "downloads": 134,
        "featured": False,
        "body": (
            "# Date Parser\n\n"
            "Extract and normalize dates from free text into ISO 8601.\n\n"
            "## Disambiguation\n\n"
            "`03/04/2024` is ambiguous between day-first and month-first locales. The "
            "parser uses the declared source locale (or infers one from surrounding "
            "values in the same column) to resolve it consistently rather than "
            "guessing per-row."
        ),
    },
]


async def seed_marketplace_demo(db: AsyncSession) -> None:
    """Insert the fixed demo catalog if it hasn't been seeded yet. Idempotent:
    a second call is a no-op (checked via the ``DEMO_WORKSPACE_ID`` marker)."""
    existing = await db.scalar(
        select(MarketplaceListing.id).where(
            MarketplaceListing.source_workspace_id == DEMO_WORKSPACE_ID
        )
    )
    if existing is not None:
        log.info("seed_marketplace_demo_skip_already_seeded")
        return

    for skill in _DEMO_SKILLS:
        slug = skill["title"].lower().replace(" ", "-")
        frontmatter = {
            "title": skill["title"],
            "type": skill["type"],
            "tags": skill["tags"],
        }
        full_markdown, body = _md(frontmatter, skill["body"])
        sha = content_sha(frontmatter, body)

        listing = MarketplaceListing(
            source_workspace_id=DEMO_WORKSPACE_ID,
            source_path=f"skills/{slug}.md",
            title=skill["title"],
            summary=skill["summary"],
            type=skill["type"],
            runtime=None,
            author_id=None,
            version="1.0.0",
            tags=skill["tags"],
            is_public=True,
            downloads=skill["downloads"],
            category=skill["category"],
            featured=skill["featured"],
        )
        db.add(listing)
        await db.flush()  # assign listing.id

        version = SkillVersion(
            listing_id=listing.id,
            version=1,
            content_sha=sha,
            changelog="Initial demo publish.",
            content=full_markdown,
        )
        db.add(version)

        listing.latest_sha = sha
        listing.latest_version = 1

    await db.commit()
    log.info("seed_marketplace_demo_complete", listings=len(_DEMO_SKILLS))
