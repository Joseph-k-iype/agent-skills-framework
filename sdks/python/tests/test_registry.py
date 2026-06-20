import json
import tempfile
from pathlib import Path
import shutil

import pytest
import yaml

from skill_sdk.registry import RegistryClient
from skill_sdk.validation import ValidationError
from skill_sdk.hashing import compute_skill_id


@pytest.fixture
def registry():
    tmp = Path(tempfile.mkdtemp())
    yield RegistryClient(tmp, auto_tag=False)
    shutil.rmtree(tmp)


@pytest.fixture
def valid_skill():
    tmp = Path(tempfile.mkdtemp())
    manifest = {
        "name": "test-skill",
        "version": "1.0.0",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
    }
    sk = tmp / "test-skill"
    sk.mkdir()
    src = sk / "src"
    src.mkdir()
    (src / "main.py").write_text("# placeholder")
    (sk / "skill.json").write_text(json.dumps(manifest))
    return sk


@pytest.fixture
def skill_with_hash(valid_skill):
    manifest_path = valid_skill / "skill.json"
    manifest = json.loads(manifest_path.read_text())
    sid = compute_skill_id(manifest, valid_skill)
    manifest["id"] = sid
    manifest_path.write_text(json.dumps(manifest))
    return valid_skill


class TestPublish:
    def test_publish_adds_hash(self, registry, valid_skill):
        result = registry.publish(valid_skill)
        assert "id" in result
        assert result["id"].startswith("skill://sha256/")
        assert result["name"] == "test-skill"
        assert result["version"] == "1.0.0"

    def test_publish_stores_manifest_with_hash(self, registry, valid_skill):
        result = registry.publish(valid_skill)
        stored_manifest = Path(result["path"]) / "skill.json"
        stored = json.loads(stored_manifest.read_text())
        assert "id" in stored
        assert stored["id"] == result["id"]

    def test_publish_duplicate_fails(self, registry, valid_skill):
        registry.publish(valid_skill)
        with pytest.raises(ValidationError, match="already published"):
            registry.publish(valid_skill)

    def test_publish_force_overwrites(self, registry, valid_skill):
        registry.publish(valid_skill)
        result = registry.publish(valid_skill, force=True)
        assert result["name"] == "test-skill"

    def test_publish_missing_manifest(self, registry):
        tmp = Path(tempfile.mkdtemp())
        with pytest.raises(ValidationError, match="No skill manifest"):
            registry.publish(tmp)

    def test_publish_invalid_manifest_fails(self, registry):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "skill.json").write_text('{"name": "no-version"}')
        with pytest.raises(ValidationError):
            registry.publish(tmp)


class TestList:
    def test_empty(self, registry):
        skills = registry.list_skills()
        assert skills == {}

    def test_after_publish(self, registry, valid_skill):
        registry.publish(valid_skill)
        skills = registry.list_skills()
        assert "test-skill" in skills
        assert skills["test-skill"]["latest"] == "1.0.0"

    def test_multiple_versions(self, registry, valid_skill):
        registry.publish(valid_skill)
        v2 = Path(tempfile.mkdtemp()) / "test-skill"
        shutil.copytree(valid_skill, v2)
        m2 = json.loads((v2 / "skill.json").read_text())
        m2["version"] = "2.0.0"
        (v2 / "skill.json").write_text(json.dumps(m2))
        (v2 / "src" / "v2.py").write_text("# v2")

        registry.publish(v2)
        skills = registry.list_skills()
        assert skills["test-skill"]["latest"] == "2.0.0"
        assert "1.0.0" in skills["test-skill"]["versions"]
        assert "2.0.0" in skills["test-skill"]["versions"]


class TestInstall:
    def test_install_latest(self, registry, valid_skill):
        registry.publish(valid_skill)
        target = Path(tempfile.mkdtemp())
        result = registry.install("test-skill", target)
        assert result.exists()
        assert (result / "skill.json").exists()
        assert (result / "src" / "main.py").exists()

    def test_install_specific_version(self, registry, valid_skill):
        registry.publish(valid_skill)
        v2 = Path(tempfile.mkdtemp()) / "test-skill"
        shutil.copytree(valid_skill, v2)
        m2 = json.loads((v2 / "skill.json").read_text())
        m2["version"] = "2.0.0"
        (v2 / "skill.json").write_text(json.dumps(m2))

        registry.publish(v2)
        target = Path(tempfile.mkdtemp())
        result = registry.install("test-skill", target, version="2.0.0")
        manifest = json.loads((result / "skill.json").read_text())
        assert manifest["version"] == "2.0.0"

    def test_install_unknown_skill(self, registry):
        with pytest.raises(ValidationError, match="not found"):
            registry.install("nonexistent", Path(tempfile.mkdtemp()))

    def test_install_unknown_version(self, registry, valid_skill):
        registry.publish(valid_skill)
        with pytest.raises(ValidationError, match="not found"):
            registry.install("test-skill", Path(tempfile.mkdtemp()), version="99.0.0")

    def test_install_existing_target(self, registry, valid_skill):
        registry.publish(valid_skill)
        target = Path(tempfile.mkdtemp())
        (target / "test-skill").mkdir()
        with pytest.raises(ValidationError, match="already exists"):
            registry.install("test-skill", target)


class TestInfo:
    def test_info(self, registry, valid_skill):
        registry.publish(valid_skill)
        info = registry.info("test-skill")
        assert info["latest"] == "1.0.0"
        assert info["versions"] == ["1.0.0"]
        assert "ids" in info
        assert "1.0.0" in info["ids"]

    def test_info_not_found(self, registry):
        with pytest.raises(ValidationError, match="not found"):
            registry.info("nonexistent")


class TestVerify:
    def test_verify_valid(self, registry, skill_with_hash):
        registry.publish(skill_with_hash)
        result = registry.verify("test-skill")
        assert result["valid"] is True

    def test_verify_nonexistent(self, registry):
        result = registry.verify("ghost")
        assert result["valid"] is False

    def test_verify_corrupted_files(self, registry, skill_with_hash):
        registry.publish(skill_with_hash)
        info = registry.info("test-skill")
        rel_path = info["locations"]["local"]
        stored_skill = registry.registry_path / rel_path
        (stored_skill / "src" / "main.py").write_text("# tampered content")
        result = registry.verify("test-skill")
        assert result["valid"] is False


class TestIndexFormat:
    def test_index_has_ids(self, registry, valid_skill):
        registry.publish(valid_skill)
        index = registry._load_index()
        assert "ids" in index["skills"]["test-skill"]
        assert "1.0.0" in index["skills"]["test-skill"]["ids"]

    def test_initial_index(self, registry):
        index = registry._load_index()
        assert index["schema_version"] == 1
        assert index["sources"] == []
        assert index["skills"] == {}


class TestEdgeCases:
    def test_publish_yaml_manifest(self, registry):
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "yaml-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
        }
        (tmp / "skill.yaml").write_text(yaml.dump(manifest))
        (tmp / "main.py").write_text("# placeholder")
        result = registry.publish(tmp)
        assert result["name"] == "yaml-skill"

    def test_publish_with_skill_dependency(self, registry):
        tmp = Path(tempfile.mkdtemp())
        manifest = {
            "name": "dependent", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "dependencies": {"skills": ["base-skill@^1.0.0"]},
        }
        (tmp / "skill.json").write_text(json.dumps(manifest))
        (tmp / "main.py").write_text("# placeholder")
        result = registry.publish(tmp)
        assert result["name"] == "dependent"

    def test_publish_and_install_preserves_hash(self, registry, skill_with_hash):
        result = registry.publish(skill_with_hash)
        original_id = result["id"]

        target = Path(tempfile.mkdtemp())
        registry.install("test-skill", target)
        installed_manifest = json.loads((target / "test-skill" / "skill.json").read_text())
        assert installed_manifest["id"] == original_id


class TestNonDestructivePublish:
    def test_source_manifest_not_mutated(self, registry, valid_skill):
        before = (valid_skill / "skill.json").read_text()
        registry.publish(valid_skill)
        after = (valid_skill / "skill.json").read_text()
        assert before == after, "publish must not modify the user's source manifest"
        assert "id" not in json.loads(after)

    def test_registry_copy_has_id(self, registry, valid_skill):
        result = registry.publish(valid_skill)
        stored = json.loads((Path(result["path"]) / "skill.json").read_text())
        assert stored["id"] == result["id"]


class TestPublishDoesNotLeakSecretsOrCaches:
    def test_dotenv_and_caches_excluded(self, registry, valid_skill):
        (valid_skill / ".env").write_text("SECRET=hunter2")
        (valid_skill / ".pytest_cache").mkdir()
        (valid_skill / ".pytest_cache" / "v").write_text("junk")
        (valid_skill / "agent.egg-info").mkdir()
        result = registry.publish(valid_skill)
        stored = Path(result["path"])
        assert not (stored / ".env").exists(), ".env must never be copied into the registry"
        assert not (stored / ".pytest_cache").exists()
        assert not (stored / "agent.egg-info").exists()


class TestSemVerLatest:
    def test_latest_is_semver_max_not_lexical(self, registry, valid_skill):
        registry.publish(valid_skill)  # 1.0.0
        for v in ("0.9.0", "0.10.0"):
            d = Path(tempfile.mkdtemp()) / "test-skill"
            shutil.copytree(valid_skill, d)
            m = json.loads((d / "skill.json").read_text())
            m["version"] = v
            (d / "skill.json").write_text(json.dumps(m))
            registry.publish(d)
        info = registry.info("test-skill")
        # Lexically "0.9.0" > "0.10.0" > "1.0.0"; SemVer max is 1.0.0.
        assert info["latest"] == "1.0.0"


class TestGitTagPersistence:
    def test_git_tag_recorded_in_index(self, tmp_path, valid_skill):
        import subprocess
        # valid_skill lives in its own tmp dir; make it a git repo so tagging runs.
        repo = valid_skill
        subprocess.run(["git", "init", "-q"], cwd=repo, check=True)
        subprocess.run(["git", "add", "-A"], cwd=repo, check=True)
        subprocess.run(
            ["git", "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "x"],
            cwd=repo, check=True,
        )
        reg = RegistryClient(tmp_path, auto_tag=True)
        result = reg.publish(repo)
        assert result["git_tag"] == "skill/test-skill/1.0.0"
        entry = reg.info("test-skill")
        assert entry.get("git_tags", {}).get("1.0.0") == "skill/test-skill/1.0.0"


class TestInstallIntegrity:
    def test_install_detects_tampered_registry(self, registry, valid_skill):
        result = registry.publish(valid_skill)
        # Tamper with the stored skill so its content no longer matches its id.
        (Path(result["path"]) / "src" / "main.py").write_text("# evil payload")
        target = Path(tempfile.mkdtemp())
        with pytest.raises(ValidationError, match="Integrity check failed"):
            registry.install("test-skill", target)
        assert not (target / "test-skill").exists(), "failed install must not leave files"


class TestConcurrentPublish:
    def test_parallel_publishes_no_lost_updates(self, registry, valid_skill):
        # Publish many distinct versions concurrently; the locked, atomic index
        # must retain every one (the old unguarded RMW dropped writers).
        import concurrent.futures

        versions = [f"1.0.{i}" for i in range(12)]
        skills = []
        for v in versions:
            d = Path(tempfile.mkdtemp()) / "test-skill"
            shutil.copytree(valid_skill, d)
            m = json.loads((d / "skill.json").read_text())
            m["version"] = v
            (d / "skill.json").write_text(json.dumps(m))
            skills.append(d)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as ex:
            list(ex.map(registry.publish, skills))

        recorded = set(registry.info("test-skill")["versions"])
        assert recorded == set(versions)
