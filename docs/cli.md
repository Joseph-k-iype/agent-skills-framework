# CLI reference (`skill`)

Entry point: `cli/src/main.py`. It inserts `sdks/python` onto `sys.path` at
import time, so it needs no installation — just run it with `python3`.

```bash
python cli/src/main.py <command> [args] [flags]
```

Every command that touches a registry accepts `--registry <path>` (default:
`./registry` relative to the current working directory).

## `init <name>`

Scaffold a new skill project.

```bash
skill init my-skill [--path <dir>] [--registry <path>]
```

Creates `<path>/SKILL.md`, `<path>/src/main.py` (a working `BaseSkill`
stub), and an empty `<path>/tests/` dir. `--path` defaults to `<name>`.

## `validate [path]`

```bash
skill validate [path=.] [--registry <path>] [--deep]
```

Runs `validate_full_skill()` against `path` (default: cwd). Exits non-zero
and prints every error if invalid. With `--deep`:

- If the manifest has an `id`, recomputes and compares it
  (`validate_skill_id`).
- Runs `detect_dependency_cycles()`, resolving transitive dependencies
  through a `RegistryClient` if `<registry>` exists.

On success, prints the skill ID (or `(not computed)`) and any non-fatal lint
warnings (`lint_full_skill()` — e.g. missing `tests/`).

## `build [path]`

```bash
skill build [path=.] [--registry <path>] [--skip-validation]
```

Validates (unless `--skip-validation`), computes the content-addressed ID,
**copies sources into `<path>/dist/` first**, then writes the manifest with
the stamped `id` into `dist/` — that ordering matters: copying after stamping
would silently overwrite the stamped manifest with the unstamped source one.
Excludes `.git`, `__pycache__`, `node_modules`, `dist`, dotfiles, and
`*.egg-info` from the copy. Prints lint warnings after a successful build.

## `publish [path]`

```bash
skill publish [path=.] [--registry <path>] [--force] [--no-tag] \
              [--graph-host <host>] [--graph-port <port>]
```

Calls `RegistryClient.publish()` — see
[content-addressing.md#non-destructive-publish](./content-addressing.md#non-destructive-publish)
for what this does and does not mutate. `--force` overwrites an existing
`name@version` in the registry. `--no-tag` skips creating the
`skill/<name>/<version>` git tag (tagging is otherwise controlled by the
registry's `auto_tag` setting).

FalkorDB graph sync now happens automatically as part of every `publish()`
call (best-effort — a failure to connect never fails the publish). Point it
at a running instance either with `--graph-host`/`--graph-port`, or by
setting the `SKILLS_GRAPH_HOST`/`SKILLS_GRAPH_PORT` env vars (the flags take
precedence when both are set). The same env vars are read by the frontend API
(`frontend/api/deps.py`), so the dashboard's publish/scaffold routes get graph
sync for free with no separate configuration. With neither set, `publish()`
behaves exactly as before — no graph dependency at all.

## `install <name>`

```bash
skill install <name> [--registry <path>] [--target <dir>] \
              [--version <version>] [--source <local|git>] [--no-verify]
```

Copies the registry's stored copy of `<name>` into `<target>/<name>`
(default target: cwd). Without `--version`, installs `latest` (SemVer max).
`--source` forces installation from a specific configured source type instead
of the local registry copy. By default, recomputes the skill ID post-copy and
fails (rolling back) on a mismatch — pass `--no-verify` to skip that check.

## `list`

```bash
skill list [--registry <path>]
```

Prints every skill's `name@latest`, a short hash prefix, and version count.

## `info <name>`

```bash
skill info <name> [--registry <path>]
```

Prints the full registry index entry for `<name>` as JSON
(`versions`, `latest`, `ids`, `locations`, `git_tags`).

## `doc [path]`

```bash
skill doc [path=.] [--format markdown|json] [--output <file>]
```

Generates documentation from the manifest via `generate_skill_doc()`. Without
`--output`, prints to stdout.

## `verify <name>`

```bash
skill verify <name> [--registry <path>] [--version <version>]
```

Recomputes the stored skill's content hash and compares it to what's recorded
in the index (defaults to `latest`). Exits non-zero with the mismatch reason
on failure. This only checks the registry's *stored copy* against its own
recorded id — it never looks at git. For that, see `verify-git` below.

## `verify-git [name]`

```bash
skill verify-git <name> [--version <version>] [--registry <path>]
skill verify-git --all [--registry <path>]
```

Cross-checks a published skill against the git tag recorded at publish time
(`skill/<name>/<version>`, as written into `index.yaml`'s `git_tags`). Checks
out that tag into a disposable `git worktree`, searches the checked-out tree
for the manifest matching `<name>@<version>`, recomputes its content-addressed
id, and compares it against the id recorded in the index — catching drift
between what's in the registry and what's actually in git history (e.g. a
skill published from an uncommitted working tree, then committed afterward
under a different tree). `--all` loops every skill in the registry instead of
one. Per skill, prints one of:

- `✓ name@version matches git tag ...` — hashes agree.
- `– name@version: skipped (no git tag recorded)` — not a failure; the skill
  was published with `--no-tag` or `auto_tag=False`, or has no recorded tag.
- `✗ name: <reason>` — hash mismatch, the tag doesn't resolve, or no manifest
  for `name@version` was found inside the tagged tree.

Exits non-zero if any skill reports a mismatch (skips don't count as
failures). `make verify-published` runs `verify-git --all` against the
repo's own `registry/`; it's wired into CI (`.github/workflows/ci.yml`) as a
non-blocking step (`continue-on-error`) since it can flag historical drift
unrelated to the current change under review.

## `sync`

```bash
skill sync [--registry <path>] [--source-type git] [--source-url <url>] \
           [--source-ref <ref=main>] [--cache <path>]
```

If `--source-type`/`--source-url` are both given, first adds that source to
the registry (`add_source`), then always runs `sync_from_sources()` —
pulling in any new versions from every configured source (local or git) and
printing the synced count plus any per-source errors.

## `graph <connect|register|query>`

```bash
skill graph connect [--graph-host <host>] [--graph-port <port>]
skill graph register [path=.] [--graph-host <host>] [--graph-port <port>]
skill graph query [--graph-host <host>] [--graph-port <port>] \
                   [--capability <cap> | --impact-id <id>]
```

Thin CLI over `FalkorDBConnector` (see
[python-sdk.md#graphpy--falkordbconnector](./python-sdk.md#graphpy--falkordbconnector)).
`connect` just tests reachability. `register` loads a skill's manifest and
mirrors it into the graph (capabilities, dependencies, *and* permissions —
each declared `{resource, actions}` permission becomes a `Permission` node
linked to the skill via a `REQUESTS` relationship). `query --impact-id <id>`
walks **forward** dependencies (`(sv)-[:DEPENDS_ON*]->(dep)`) — i.e. what the
given skill depends on, not what would break if it changed. For the inverse
("what's downstream of this skill"), use the registry-only
`/skills/{name}/impact` endpoint described in
[frontend.md](./frontend.md#governance), not this command. All three graph
subcommands require a reachable FalkorDB/Redis instance — there is no
local-only fallback at the CLI layer (the dashboard's Knowledge Graph page
has one; the CLI does not). Permission-based graph lookups
(`find_skills_by_permission`) are currently only exposed through the frontend
API's `/graph/query` route (`permission_resource` param), not this CLI.
