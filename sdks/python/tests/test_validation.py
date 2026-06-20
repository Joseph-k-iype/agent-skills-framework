import json
import tempfile
from pathlib import Path

import pytest
import yaml

from skill_sdk.validation import (
    validate_manifest,
    validate_manifest_file,
    validate_full_skill,
    validate_manifest_with_path,
    detect_dependency_cycles,
    ValidationError,
    load_manifest,
)
from skill_sdk.hashing import compute_skill_id


def test_valid_manifest():
    manifest = {
        "name": "test-skill",
        "version": "1.0.0",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
    }
    errors = validate_manifest(manifest)
    assert errors == []


def test_missing_required_fields():
    manifest = {"name": "test"}
    errors = validate_manifest(manifest)
    required = {"version", "runtime", "api_version", "entry"}
    missing = {e.split("'")[1] for e in errors if "Missing" in e}
    assert missing == required


class TestNameValidation:
    def test_invalid_name_capitals(self):
        errors = validate_manifest({
            "name": "InvalidName",
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert any("kebab-case" in e for e in errors)

    def test_name_too_short(self):
        errors = validate_manifest({
            "name": "a",
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert any("too short" in e for e in errors)

    def test_name_too_long(self):
        errors = validate_manifest({
            "name": "a" * 65,
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert any("too long" in e for e in errors)

    def test_name_not_string(self):
        errors = validate_manifest({
            "name": 123,
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert any("must be a string" in e for e in errors)


class TestVersionValidation:
    def test_invalid_version_format(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "v1.0",
            "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert any("SemVer" in e for e in errors)

    def test_version_not_string(self):
        errors = validate_manifest({
            "name": "test-skill", "version": 1,
            "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert any("must be a string" in e for e in errors)


class TestRuntimeValidation:
    def test_invalid_runtime(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "rust",
            "api_version": 1, "entry": "main.py",
        })
        assert any("runtime" in e for e in errors)

    def test_runtime_not_string(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": 123,
            "api_version": 1, "entry": "main.py",
        })
        assert any("must be a string" in e for e in errors)


class TestApiVersionValidation:
    def test_api_version_not_int(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": "1", "entry": "main.py",
        })
        assert any("must be an integer" in e for e in errors)

    def test_api_version_below_one(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 0, "entry": "main.py",
        })
        assert any(">= 1" in e for e in errors)


class TestEntryValidation:
    def test_python_entry_must_be_py(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "src/main.ts",
        })
        assert any(".py" in e for e in errors)

    def test_typescript_entry_must_be_ts_or_js(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "typescript",
            "api_version": 1, "entry": "src/main.py",
        })
        assert any(".ts" in e or ".js" in e for e in errors)

    def test_entry_not_string(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": 42,
        })
        assert any("must be a string" in e for e in errors)


class TestTriggerValidation:
    def test_invalid_command_no_slash(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "triggers": {"commands": ["no-slash"]},
        })
        assert any("'/" in e for e in errors)

    def test_command_not_string(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "triggers": {"commands": [42]},
        })
        assert any("must be a string" in e for e in errors)

    def test_event_empty_string(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "triggers": {"events": [""]},
        })
        assert any("empty" in e for e in errors)

    def test_triggers_not_dict(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "triggers": "not-a-dict",
        })
        assert any("must be a dict" in e for e in errors)


class TestCapabilitiesValidation:
    def test_capabilities_not_list(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "capabilities": "not-a-list",
        })
        assert any("must be a list" in e for e in errors)

    def test_capability_empty(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "capabilities": [""],
        })
        assert any("empty" in e for e in errors)


class TestDependencyValidation:
    def test_unknown_dep_type(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"maven": ["foo:bar"]},
        })
        assert any("maven" in e for e in errors)

    def skill_dep_without_version(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["other-skill"]},
        })
        assert any("must specify version" in e for e in errors)

    def test_skill_dep_bad_name(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["BadName@^1.0.0"]},
        })
        assert any("Invalid" in e for e in errors)

    def test_dep_not_list(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"pip": "not-a-list"},
        })
        assert any("must be a list" in e for e in errors)


class TestPermissionValidation:
    def test_permission_missing_resource(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "permissions": [{"actions": ["read"]}],
        })
        assert any("resource" in e for e in errors)

    def test_invalid_action(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "permissions": [{"resource": "db", "actions": ["destroy"]}],
        })
        assert any("destroy" in e for e in errors)

    def test_permission_not_list(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "permissions": "not-a-list",
        })
        assert any("must be a list" in e for e in errors)

    def test_permission_item_not_dict(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "permissions": ["string-not-dict"],
        })
        assert any("must be a dict" in e for e in errors)


class TestLifecycleValidation:
    def test_unknown_hook(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "lifecycle": {"on_foo": "script.sh"},
        })
        assert any("on_foo" in e for e in errors)

    def test_lifecycle_not_dict(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "lifecycle": ["not-a-dict"],
        })
        assert any("must be a dict" in e for e in errors)


class TestIdValidation:
    def test_valid_id(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "id": "skill://sha256/1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef/test-skill@1.0.0",
        })
        assert errors == []

    def test_invalid_id_format(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "id": "not-a-valid-id",
        })
        assert any("Invalid id format" in e for e in errors)

    def test_id_not_string(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "id": 42,
        })
        assert any("must be a string" in e for e in errors)


class TestCycleDetection:
    def test_no_cycle(self):
        manifest = {
            "name": "a",
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["b@^1.0.0"]},
        }
        errors = detect_dependency_cycles(manifest)
        assert errors == []

    def test_self_cycle(self):
        manifest = {
            "name": "a",
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["a@^1.0.0"]},
        }
        errors = detect_dependency_cycles(manifest)
        assert len(errors) > 0

    def test_no_deps_no_cycle(self):
        manifest = {
            "name": "a",
            "version": "1.0.0", "runtime": "python", "api_version": 1, "entry": "main.py",
        }
        errors = detect_dependency_cycles(manifest)
        assert errors == []


class TestFullSkillValidation:
    def test_missing_manifest_dir(self):
        tmp = Path(tempfile.mkdtemp())
        errors = validate_full_skill(tmp)
        assert any("No skill.yaml" in e for e in errors)

    def test_missing_entry_point(self):
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "src/missing.py",
        }
        (tmp / "skill.json").write_text(json.dumps(manifest))
        errors = validate_full_skill(tmp)
        assert any("not found" in e for e in errors)


class TestManifestFileValidation:
    def test_validate_yaml_manifest(self):
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "yaml-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
        }
        path = tmp / "skill.yaml"
        path.write_text(yaml.dump(manifest))
        errors = validate_manifest_file(path)
        assert errors == []

    def test_validate_file_not_found(self):
        errors = validate_manifest_file("/nonexistent/skill.json")
        assert any("not found" in e for e in errors)

    def test_manifest_not_object(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "skill.json"
        path.write_text('"just-a-string"')
        errors = validate_manifest_file(path)
        assert any("must be" in e for e in errors)

    def test_manifest_with_hash_validation(self):
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "hash-test", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
        }
        path = tmp / "skill.json"
        path.write_text(json.dumps(manifest))
        (tmp / "main.py").write_text("# placeholder")

        sid = compute_skill_id(manifest, tmp)
        manifest["id"] = sid
        path.write_text(json.dumps(manifest))

        errors = validate_manifest_file(path)
        assert errors == []

    def test_manifest_with_bad_hash(self):
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "bad-hash", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "id": "skill://sha256/aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa/bad-hash@1.0.0",
        }
        path = tmp / "skill.json"
        path.write_text(json.dumps(manifest))
        (tmp / "main.py").write_text("# placeholder")

        errors = validate_manifest_file(path)
        assert any("mismatch" in e for e in errors)


class TestLoadManifest:
    def test_load_yaml(self):
        tmp = Path(tempfile.mkdtemp())
        manifest = {"name": "yaml-test", "version": "1.0.0", "runtime": "python",
                     "api_version": 1, "entry": "main.py"}
        path = tmp / "skill.yaml"
        path.write_text(yaml.dump(manifest))
        result = load_manifest(path)
        assert result["name"] == "yaml-test"

    def test_load_not_found(self):
        with pytest.raises(ValidationError, match="not found"):
            load_manifest("/nonexistent/")

    def test_load_invalid_yaml(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "skill.yaml"
        path.write_text(": invalid yaml [[")
        with pytest.raises(ValidationError):
            load_manifest(path)

    def test_load_with_validation_errors(self):
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "skill.json"
        path.write_text('{"name": "test"}')
        with pytest.raises(ValidationError, match="validation failed"):
            load_manifest(path)


class TestMalformedJsonManifest:
    def test_malformed_json_returns_clean_error_not_crash(self):
        # Regression: validate_manifest_file referenced `yaml` in the except
        # clause while parsing JSON, raising NameError/UnboundLocalError.
        tmp = Path(tempfile.mkdtemp())
        path = tmp / "skill.json"
        path.write_text('{"name": "x", BROKEN}')
        errors = validate_manifest_file(path)
        assert any("Invalid manifest format" in e for e in errors)


class TestFullSemVerVersions:
    def test_prerelease_version_accepted(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.2.3-rc.1",
            "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert errors == []

    def test_build_metadata_version_accepted(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.2.3-rc.1+build.9",
            "runtime": "python", "api_version": 1, "entry": "main.py",
        })
        assert errors == []

    def test_id_with_prerelease_version_accepted(self):
        errors = validate_manifest({
            "name": "test-skill", "version": "1.0.0-rc.1",
            "runtime": "python", "api_version": 1, "entry": "main.py",
            "id": f"skill://sha256/{'a'*64}/test-skill@1.0.0-rc.1",
        })
        assert errors == []


class TestTestsDirNotAnError:
    def test_missing_tests_dir_does_not_fail_validation(self):
        # Regression: build/validate used to fail because a missing tests/ dir
        # was appended as a hard error.
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "test-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
        }
        (tmp / "skill.json").write_text(json.dumps(manifest))
        (tmp / "main.py").write_text("# placeholder")
        errors = validate_full_skill(tmp)
        assert errors == []

    def test_lint_reports_missing_tests_as_warning(self):
        from skill_sdk.validation import lint_full_skill
        tmp = Path(tempfile.mkdtemp())
        warnings = lint_full_skill(tmp)
        assert any("tests" in w for w in warnings)


class TestTransitiveCycleDetection:
    class FakeRegistry:
        def __init__(self, graph):
            self.graph = graph

        def get_skill_dependencies(self, name):
            return self.graph.get(name, [])

    def test_transitive_cycle_detected(self):
        # a -> b -> a  (a's deps come from the manifest, b's from the registry)
        manifest = {
            "name": "a", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["b@^1.0.0"]},
        }
        reg = self.FakeRegistry({"b": ["a"]})
        errors = detect_dependency_cycles(manifest, reg)
        assert len(errors) > 0

    def test_longer_cycle_detected(self):
        # a -> b -> c -> a
        manifest = {
            "name": "a", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["b@^1.0.0"]},
        }
        reg = self.FakeRegistry({"b": ["c"], "c": ["a"]})
        errors = detect_dependency_cycles(manifest, reg)
        assert len(errors) > 0

    def test_no_cycle_dag(self):
        manifest = {
            "name": "a", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["b@^1.0.0", "c@^1.0.0"]},
        }
        reg = self.FakeRegistry({"b": ["c"], "c": []})
        errors = detect_dependency_cycles(manifest, reg)
        assert errors == []
