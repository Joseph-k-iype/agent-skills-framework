# Getting started

Requirements: Python 3.11+, Node 18+ (for the TypeScript SDK and dashboard).
Only third-party Python deps are `pyyaml` and `pydantic`; FalkorDB graph
features additionally need `redis` (optional — everything else works without
it).

## CLI: author, validate, and publish a skill

```bash
# scaffold a new skill
python cli/src/main.py init my-skill
cd my-skill

# validate structurally, then deeply (hash + dependency-cycle checks)
python ../cli/src/main.py validate
python ../cli/src/main.py validate --deep

# compute the content-addressed id and stage a dist/ build
python ../cli/src/main.py build

# publish into ../registry (creates registry/skills/my-skill-0.1.0/, updates index.yaml)
python ../cli/src/main.py publish

# discover what's published
python ../cli/src/main.py list
python ../cli/src/main.py info my-skill

# install a copy elsewhere, with integrity re-verification
python ../cli/src/main.py install my-skill --target /tmp/somewhere
```

Every subcommand accepts `--registry <path>` (default: `./registry` relative
to your cwd). Full flag reference: [cli.md](./cli.md).

## Run every test suite

```bash
make install-ts   # first time only — installs sdks/typescript's npm deps
make test         # runs Python SDK, CLI, reference skill, harness, and TypeScript suites
```

Or run one suite at a time: `make test-sdk | test-cli | test-skill |
test-harness | test-ts`. See [testing.md](./testing.md) for what each suite
covers and how to run a single test file.

## Run the dashboard

```bash
cd frontend
pip install -r api/requirements.txt
npm install
npm run dev:all   # starts FastAPI on :8000 and Vite on :5173 together
```

Open `http://localhost:5173`. Full feature list, API surface, and config:
[frontend.md](./frontend.md).

## Lint

```bash
cd sdks/python && ruff check .
```

Config: `sdks/python/pyproject.toml` (ruff, line-length 100, rules E/F/I/UP).
