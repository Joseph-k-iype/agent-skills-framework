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
registry's `auto_tag` setting). If `--graph-host` is given, also attempts to
register the published skill into a running FalkorDB instance afterward
(best-effort — failure to connect doesn't fail the publish).

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
on failure.

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
mirrors it into the graph. `query` looks up skills by capability or runs
impact analysis from a skill ID. All three require a reachable FalkorDB/Redis
instance — there is no local-only fallback at the CLI layer (the dashboard's
Knowledge Graph page has one; the CLI does not).
