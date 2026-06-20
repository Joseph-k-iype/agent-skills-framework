# Security model — Agent Skills Dashboard

This dashboard is treated as a **shared/hosted** service. Read this before exposing it beyond localhost.

## Path sandboxing

Every endpoint that accepts a server-side filesystem path (`build`, `publish`,
`scaffold`, `install` target, `graph/register`, local registry `sources`) routes
that path through `api.security.resolve_in_workspace()`. Paths are confined to a
**workspace root**:

- Default: `<repo>/workspace`
- Override: set the `SKILLS_WORKSPACE` environment variable.

Relative paths are joined to the root; absolute paths must already live inside
it. Traversal (`..`) or any path that escapes the root is rejected with HTTP 400.
Skills are scaffolded into `<workspace>/<name>` and installed into
`<workspace>/installed/<name>` by default.

## API authentication

Mutating endpoints (install / build / publish / scaffold / add-source / sync /
graph-register) are gated by an **opt-in API key**:

- Unset `SKILLS_API_KEY` → gate disabled (local dev convenience).
- Set `SKILLS_API_KEY=<value>` → callers must send `X-API-Key: <value>` or
  `Authorization: Bearer <value>`. The frontend reads `VITE_API_KEY` at build
  time and attaches the header automatically.

Read endpoints stay open even when a key is set; put the service behind your own
gateway if reads must also be protected.

## Known gap: per-user authorization

The frontend **role switcher is a UX preview only** — it changes which controls
are visible, not what the server will accept. There is no per-user identity or
role enforcement on the backend; the API key is a single shared secret. For real
multi-tenant authz, place this behind an authenticating reverse proxy / identity
provider and map identities to permissions server-side. This is an intentional,
documented limitation, surfaced in the Settings page.

## CORS

The API allows the Vite dev origin (`localhost:5173`). In production the frontend
is served same-origin via a reverse proxy, so CORS is not relied upon; tighten
`allow_origins` for any direct cross-origin access.
