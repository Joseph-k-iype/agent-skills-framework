from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "sdks" / "python"))

from skill_sdk.validation import (
    load_manifest,
    find_manifest_file,
    _parse_frontmatter,
    ValidationError,
    validate_full_skill,
    lint_full_skill,
)
from skill_sdk.registry import RegistryClient
from skill_sdk.hashing import compute_skill_id, validate_skill_id
from skill_sdk.adapter import generate_skill_doc
from skill_sdk.graph import FalkorDBConnector
from skill_sdk.git_verify import verify_against_git

GRAPH_HOST_ENV = "SKILLS_GRAPH_HOST"
GRAPH_PORT_ENV = "SKILLS_GRAPH_PORT"


def _get_registry(args) -> RegistryClient:
    host = getattr(args, "graph_host", None) or os.environ.get(GRAPH_HOST_ENV)
    graph = None
    if host:
        port = getattr(args, "graph_port", None) or int(os.environ.get(GRAPH_PORT_ENV, 6379))
        graph = FalkorDBConnector(host=host, port=port, enabled=True)
    return RegistryClient(args.registry or Path.cwd() / "registry", graph=graph)


def cmd_init(args):
    name = args.name
    path = Path(args.path or name)
    if path.exists():
        print(f"Error: directory '{path}' already exists")
        sys.exit(1)

    path.mkdir(parents=True)
    src = path / "src"
    src.mkdir()
    tests = path / "tests"
    tests.mkdir()

    manifest_lines = []
    manifest_lines.append(f"name: {name}")
    manifest_lines.append("version: 0.1.0")
    manifest_lines.append(f"description: Description of {name}")
    manifest_lines.append("runtime: python")
    manifest_lines.append("api_version: 1")
    manifest_lines.append("entry: src/main.py")
    manifest_lines.append("")
    manifest_lines.append("triggers:")
    manifest_lines.append("  events: []")
    manifest_lines.append("  commands: []")
    manifest_lines.append("capabilities: []")
    manifest_lines.append("")
    manifest_lines.append("config:")
    manifest_lines.append("  required: []")
    manifest_lines.append("  schema: {}")
    manifest_lines.append("")
    manifest_lines.append("dependencies:")
    manifest_lines.append("  pip: []")
    manifest_lines.append("  npm: []")
    manifest_lines.append("  skills: []")
    manifest_lines.append("permissions: []")

    body = f"""# {name}

Instructions for the AI agent using this skill.

## Overview

{name} is a skill that does something useful.

## Usage

Describe how to interact with this skill.

## Examples

Provide example interactions.
"""
    text = "---\n" + "\n".join(manifest_lines) + "\n---\n\n" + body.lstrip()
    manifest_path = path / "SKILL.md"
    manifest_path.write_text(text, encoding="utf-8")

    main_py = src / "main.py"
    code = '''from skill_sdk import BaseSkill, SkillContext, SkillEvent, SkillCommand, SkillResult, HealthStatus


class Skill(BaseSkill):
    name = "{name}"
    version = "0.1.0"

    async def initialize(self, ctx: SkillContext) -> None:
        self.logger = ctx.logger

    async def handle_event(self, event: SkillEvent) -> SkillResult:
        return SkillResult(status="success", message=f"Received event: {{event.name}}")

    async def handle_command(self, command: SkillCommand) -> SkillResult:
        return SkillResult(status="success", message=f"Executed command: {{command.name}}")

    async def health_check(self) -> HealthStatus:
        return HealthStatus(healthy=True, version=self.version)

    async def shutdown(self) -> None:
        pass
'''.format(name=name)
    main_py.write_text(code, encoding="utf-8")

    print(f"Skill '{name}' scaffolded at {path}")
    print(f"  Manifest: {manifest_path}")
    print(f"  Entry:    {main_py}")
    print(f"  Tests:    {tests}")
    print(f"\nNext steps:")
    print(f"  cd {path}")
    print(f"  skill validate")
    print(f"  skill publish")


def cmd_validate(args):
    target = Path(args.path)
    manifest_file = find_manifest_file(target)
    if not manifest_file:
        print(f"Error: no SKILL.md, skill.yaml, skill.yml, or skill.json found in {target}")
        sys.exit(1)

    errors = validate_full_skill(target)

    if args.deep:
        manifest = load_manifest(manifest_file)
        if manifest.get("id"):
            id_errors = validate_skill_id(manifest, target)
            errors.extend(id_errors)

        from skill_sdk.validation import detect_dependency_cycles
        registry = None
        registry_dir = Path(args.registry) if args.registry else Path.cwd() / "registry"
        if registry_dir.exists():
            registry = RegistryClient(registry_dir, auto_tag=False)
        cycle_errors = detect_dependency_cycles(manifest, registry)
        errors.extend(cycle_errors)

    if errors:
        print(f"✗ {len(errors)} validation error(s):")
        for err in errors:
            print(f"  - {err}")
        sys.exit(1)

    manifest = load_manifest(manifest_file)
    sid = manifest.get("id", "(not computed)")
    print(f"✓ Valid: {manifest['name']}@{manifest['version']}")
    print(f"  ID: {sid}")
    for warning in lint_full_skill(target):
        print(f"  ⚠ {warning}")


def cmd_build(args):
    target = Path(args.path)
    manifest_file = find_manifest_file(target)
    if not manifest_file:
        print(f"Error: no SKILL.md, skill.yaml, skill.yml, or skill.json found in {target}")
        sys.exit(1)

    if not args.skip_validation:
        errors = validate_full_skill(target)
        if errors:
            print(f"✗ Build failed: {len(errors)} validation error(s)")
            for err in errors:
                print(f"  - {err}")
            sys.exit(1)

    manifest = load_manifest(manifest_file)
    name = manifest["name"]
    version = manifest["version"]

    skill_id = compute_skill_id(manifest, target)
    manifest["id"] = skill_id

    import shutil
    import yaml

    dist = target / "dist"
    if dist.exists():
        shutil.rmtree(dist)
    dist.mkdir(parents=True)

    # Copy sources first (excluding junk/secrets), THEN stamp the manifest — the
    # previous order let the copy loop overwrite the id'd manifest with the
    # source manifest, producing a dist whose manifest lacked the computed id.
    _ignore = {".git", "__pycache__", "node_modules", "dist"}
    for item in target.iterdir():
        if item.name in _ignore or item.name.startswith(".") or item.name.endswith(".egg-info"):
            continue
        if item.is_dir():
            shutil.copytree(item, dist / item.name, dirs_exist_ok=True)
        else:
            shutil.copy2(item, dist / item.name)

    dest_manifest = dist / manifest_file.name
    if manifest_file.name == "SKILL.md":
        old_body = ""
        try:
            from skill_sdk.validation import _parse_frontmatter
            raw = dest_manifest.read_text(encoding="utf-8")
            parsed = _parse_frontmatter(raw)
            if parsed:
                _, old_body = parsed
        except Exception:
            pass
        frontmatter = yaml.dump(manifest, default_flow_style=False, sort_keys=False).strip()
        text = f"---\n{frontmatter}\n---"
        if old_body.strip():
            text += f"\n\n{old_body.strip()}\n"
        dest_manifest.write_text(text, encoding="utf-8")
    elif manifest_file.suffix in (".yaml", ".yml"):
        dest_manifest.write_text(
            yaml.dump(manifest, default_flow_style=False, sort_keys=False), encoding="utf-8"
        )
    else:
        dest_manifest.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")

    print(f"✓ Built: {name}@{version}")
    print(f"  ID: {skill_id}")
    print(f"  Output: {dist}")
    for warning in lint_full_skill(target):
        print(f"  ⚠ {warning}")


def cmd_publish(args):
    target = Path(args.path)
    registry = _get_registry(args)

    try:
        result = registry.publish(target, force=args.force, tag=False if args.no_tag else None)
        print(f"✓ Published {result['name']}@{result['version']}")
        print(f"  ID: {result['id']}")
        print(f"  Location: {result['path']}")
        if result.get("git_tag"):
            print(f"  Git tag: {result['git_tag']}")

        graph_result = result.get("graph")
        if graph_result and graph_result.get("status") == "registered":
            print(f"  Graph: registered [{graph_result['id']}]")
        elif graph_result and graph_result.get("status") == "error":
            print(f"  Graph: error ({graph_result['error']})")

    except ValidationError as e:
        print(f"✗ Publish failed: {e}")
        sys.exit(1)


def cmd_install(args):
    registry = _get_registry(args)
    try:
        target = registry.install(
            args.name,
            args.target,
            version=args.version,
            source=args.source,
            verify=not args.no_verify,
        )
        print(f"✓ Installed '{args.name}' to {target}")
    except ValidationError as e:
        print(f"✗ Install failed: {e}")
        sys.exit(1)


def cmd_list(args):
    registry = _get_registry(args)
    skills = registry.list_skills()
    if not skills:
        print("No skills in registry")
        return

    print(f"Skills in registry ({len(skills)}):")
    for name, info in sorted(skills.items()):
        ids = info.get("ids", {})
        current_id = ids.get(info["latest"], "")
        hash_short = current_id.split("/")[3][:12] if current_id and "/" in current_id else ""
        print(f"  {name}@{info['latest']}  [{hash_short}...]  (versions: {len(info['versions'])})")


def cmd_info(args):
    registry = _get_registry(args)
    try:
        info = registry.info(args.name)
        print(json.dumps(info, indent=2))
    except ValidationError as e:
        print(f"✗ {e}")
        sys.exit(1)


def cmd_doc(args):
    target = Path(args.path)
    manifest_file = find_manifest_file(target)
    if not manifest_file:
        print(f"Error: no SKILL.md, skill.yaml, skill.yml, or skill.json found in {target}")
        sys.exit(1)

    try:
        text = generate_skill_doc(manifest_file, format=args.format, output_path=args.output)
        if args.output:
            print(f"✓ Generated {args.format} documentation: {args.output}")
        else:
            print(text)
    except Exception as e:
        print(f"✗ Documentation generation failed: {e}")
        sys.exit(1)


def cmd_verify(args):
    registry = _get_registry(args)
    try:
        result = registry.verify(args.name, args.version)
        if result.get("valid"):
            print(f"✓ Verified: {result['name']}@{result['version']}")
            print(f"  ID: {result.get('id', '(unknown)')}")
        else:
            print(f"✗ Verification failed:")
            for err in result.get("errors", []):
                print(f"  - {err}")
            sys.exit(1)
    except ValidationError as e:
        print(f"✗ {e}")
        sys.exit(1)


def cmd_verify_git(args):
    if not args.all and not args.name:
        print("✗ Provide a skill name or pass --all")
        sys.exit(1)

    registry = _get_registry(args)
    names = list(registry.list_skills().keys()) if args.all else [args.name]

    failures = 0
    for name in names:
        result = verify_against_git(registry, name, args.version)
        if result["valid"] is True:
            print(f"✓ {result['name']}@{result['version']} matches git tag {result['git_tag']}")
        elif result["valid"] is None:
            print(f"– {result['name']}@{result.get('version', '?')}: skipped ({result['reason']})")
        else:
            failures += 1
            print(f"✗ {name}: {'; '.join(result.get('errors', ['verification failed']))}")

    if failures:
        sys.exit(1)


def cmd_sync(args):
    registry = _get_registry(args)
    try:
        if args.source_type and args.source_url:
            source_config = {
                "type": args.source_type,
                "url": args.source_url,
                "ref": args.source_ref or "main",
            }
            if args.cache:
                source_config["cache"] = args.cache
            result = registry.add_source(source_config)
            print(f"✓ Added source: {result['source']['type']}")
        sync_result = registry.sync_from_sources()
        print(f"✓ Synced {sync_result['synced']} skill(s) from sources")
        for err in sync_result.get("errors", []):
            print(f"  ⚠ source error: {err}")
    except Exception as e:
        print(f"✗ Sync failed: {e}")
        sys.exit(1)


def cmd_graph(args):
    host = args.graph_host or "localhost"
    port = args.graph_port or 6379

    if args.command == "connect":
        graph = FalkorDBConnector(host=host, port=port)
        import asyncio
        connected = asyncio.run(graph.connect())
        if connected:
            print(f"✓ Connected to FalkorDB at {host}:{port}")
            graph.disconnect()
        else:
            print(f"✗ Could not connect to FalkorDB at {host}:{port}")
            sys.exit(1)

    elif args.command == "register":
        target = Path(args.path or ".")
        manifest_file = find_manifest_file(target)
        if not manifest_file:
            print(f"Error: no SKILL.md, skill.yaml, skill.yml, or skill.json found")
            sys.exit(1)
        graph = FalkorDBConnector(host=host, port=port)
        import asyncio
        connected = asyncio.run(graph.connect())
        if not connected:
            print(f"✗ Could not connect to FalkorDB at {host}:{port}")
            sys.exit(1)
        result = graph.register_skill(manifest_file)
        print(json.dumps(result, indent=2))
        graph.disconnect()

    elif args.command == "query":
        graph = FalkorDBConnector(host=host, port=port)
        import asyncio
        connected = asyncio.run(graph.connect())
        if not connected:
            print(f"✗ Could not connect to FalkorDB")
            sys.exit(1)
        if args.capability:
            results = graph.find_skills_by_capability(args.capability)
            print(json.dumps(results, indent=2))
        elif args.impact_id:
            results = graph.find_impact(args.impact_id)
            print(json.dumps(results, indent=2))
        graph.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Agent Skills CLI — build, validate, publish, and manage enterprise agent skills"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init_p = sub.add_parser("init", help="Scaffold a new skill project")
    init_p.add_argument("name", help="Skill name (kebab-case)")
    init_p.add_argument("--path", help="Target directory (default: skill name)")
    init_p.add_argument("--registry", help="Path to registry directory")

    val_p = sub.add_parser("validate", help="Validate a skill manifest")
    val_p.add_argument("path", nargs="?", default=".", help="Skill directory")
    val_p.add_argument("--registry", help="Path to registry directory")
    val_p.add_argument("--deep", action="store_true", help="Deep validation (hash check, dep cycle detection)")

    build_p = sub.add_parser("build", help="Build a skill (validate + compute hash + package)")
    build_p.add_argument("path", nargs="?", default=".", help="Skill directory")
    build_p.add_argument("--registry", help="Path to registry directory")
    build_p.add_argument("--skip-validation", action="store_true", help="Skip validation")

    pub_p = sub.add_parser("publish", help="Publish skill to registry with hash ID and optional git tag")
    pub_p.add_argument("path", nargs="?", default=".", help="Skill directory")
    pub_p.add_argument("--registry", help="Path to registry directory")
    pub_p.add_argument("--force", action="store_true", help="Overwrite existing publish")
    pub_p.add_argument("--no-tag", action="store_true", help="Skip creating git tag")
    pub_p.add_argument("--graph-host", help="FalkorDB host to register skill graph")
    pub_p.add_argument("--graph-port", type=int, help="FalkorDB port")

    inst_p = sub.add_parser("install", help="Install a skill from registry")
    inst_p.add_argument("name", help="Skill name")
    inst_p.add_argument("--registry", help="Path to registry directory")
    inst_p.add_argument("--target", help="Install target directory (default: cwd)")
    inst_p.add_argument("--version", help="Specific version to install")
    inst_p.add_argument("--source", help="Source type (local, git)")
    inst_p.add_argument("--no-verify", action="store_true", help="Skip post-install integrity check")

    list_p = sub.add_parser("list", help="List skills in registry")
    list_p.add_argument("--registry", help="Path to registry directory")

    info_p = sub.add_parser("info", help="Show skill details")
    info_p.add_argument("name", help="Skill name")
    info_p.add_argument("--registry", help="Path to registry directory")

    doc_p = sub.add_parser("doc", help="Generate documentation for a skill")
    doc_p.add_argument("path", nargs="?", default=".", help="Skill directory")
    doc_p.add_argument("--format", default="markdown", choices=["markdown", "json"], help="Output format")
    doc_p.add_argument("--output", help="Output file path")

    verify_p = sub.add_parser("verify", help="Verify a published skill's integrity")
    verify_p.add_argument("name", help="Skill name")
    verify_p.add_argument("--registry", help="Path to registry directory")
    verify_p.add_argument("--version", help="Version to verify (default: latest)")

    verify_git_p = sub.add_parser(
        "verify-git", help="Cross-check a published skill's id against its git tag"
    )
    verify_git_p.add_argument("name", nargs="?", help="Skill name (omit with --all)")
    verify_git_p.add_argument("--registry", help="Path to registry directory")
    verify_git_p.add_argument("--version", help="Version to verify (default: latest)")
    verify_git_p.add_argument("--all", action="store_true", help="Verify every skill with a recorded git tag")

    sync_p = sub.add_parser("sync", help="Sync registry from remote sources")
    sync_p.add_argument("--registry", help="Path to registry directory")
    sync_p.add_argument("--source-type", choices=["git"], help="Source type to add")
    sync_p.add_argument("--source-url", help="Source URL")
    sync_p.add_argument("--source-ref", default="main", help="Git branch/ref")
    sync_p.add_argument("--cache", help="Local cache path for git source")

    graph_p = sub.add_parser("graph", help="FalkorDB knowledge graph operations")
    graph_sub = graph_p.add_subparsers(dest="command", required=True)
    graph_connect = graph_sub.add_parser("connect", help="Test FalkorDB connection")
    graph_connect.add_argument("--graph-host", help="FalkorDB host")
    graph_connect.add_argument("--graph-port", type=int, help="FalkorDB port")

    graph_register = graph_sub.add_parser("register", help="Register a skill in the knowledge graph")
    graph_register.add_argument("path", nargs="?", default=".", help="Skill directory")
    graph_register.add_argument("--graph-host", help="FalkorDB host")
    graph_register.add_argument("--graph-port", type=int, help="FalkorDB port")

    graph_query = graph_sub.add_parser("query", help="Query the knowledge graph")
    graph_query.add_argument("--graph-host", help="FalkorDB host")
    graph_query.add_argument("--graph-port", type=int, help="FalkorDB port")
    graph_query.add_argument("--capability", help="Find skills by capability")
    graph_query.add_argument("--impact-id", help="Find impact analysis for a skill ID")

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "validate": cmd_validate,
        "build": cmd_build,
        "publish": cmd_publish,
        "install": cmd_install,
        "list": cmd_list,
        "info": cmd_info,
        "doc": cmd_doc,
        "verify": cmd_verify,
        "verify-git": cmd_verify_git,
        "sync": cmd_sync,
        "graph": cmd_graph,
    }

    commands[args.command](args)


if __name__ == "__main__":
    main()
