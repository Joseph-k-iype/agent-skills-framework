# Phase 3b — Marketplace v2 (storefront + SDK consumption)

Status: approved 2026-06-29. Corrects the earlier internal-install model: the
marketplace is a public storefront; skills are consumed from OUTSIDE the solution
via an SDK authenticated by API keys (the "gateway URL + key, no config" pattern
used by Smithery/Glama). Visual = a vibrant storefront (keep the Tesla Red
#E82127 palette; extend with type accents/gradients), not an admin grid.

## Backend

- `api_keys` table: user_id, name, prefix (shown), key_hash (sha256 of full key —
  secret stored only as hash), last_used_at, revoked_at. Create returns the full
  `sk_live_…` once; list returns prefixes; delete revokes.
- `require_api_key` dependency: `Authorization: Bearer sk_…` → hash → user;
  bumps last_used_at; rejects revoked/unknown.
- `usage_events` table: listing_id, user_id, kind (`fetch`|`apply`), meta JSONB.
- Endpoints:
  - JWT: `GET/POST/DELETE /api-keys`.
  - API-key: `GET /sdk/skill/{listing_id}` (content + metadata, records a `fetch`),
    `POST /sdk/usage` ({listing_id, kind, meta} → records `apply`, bumps listing
    `downloads` used as the "uses" counter).
- Remove the install-into-workspace endpoint + UI. Listing/catalog/detail stay.
- Analytics "most-used" derives from `usage_events`/listing uses.

## Python SDK (`sdk/python/`)

- `pip install eakso`; `Client(api_key, base_url).skill(id)` fetches content; 
  `skill.apply(llm, input)` wraps the body as the system prompt around the
  caller's `llm(system, user)` callable and auto-reports an `apply` usage event;
  `skill.content` / `.system_prompt` exposed. httpx-based; unit-tested with mocks.

## Frontend (vibrant storefront)

- MarketplacePage: hero + search with sort (Most used / Recently updated /
  Newest), category/type chips, a Featured (most-used) row, rich cards (type icon
  + accent color, author + verified badge, tags, uses + version + updated).
- Skill detail page `/marketplace/:id`: title/description/tags/version, a prominent
  "Use via SDK" panel (`pip install eakso` + a real snippet with the skill id +
  API-key placeholder + create-key link), content preview, version list, stats.
- Settings → API Keys page: create (copy-once modal), list with prefix, revoke.
- Palette: keep #E82127; extend with per-type accents + subtle gradients.

## Cross-cutting

- Best-effort usage recording. New migration for api_keys + usage_events.
- Tests: api-key create/auth/revoke, sdk fetch+usage endpoints, Python SDK
  (mocked HTTP), usage → analytics; frontend tsc/eslint/build.
