import json
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest
import yaml

from skill_sdk.git_verify import verify_against_git
from skill_sdk.registry import RegistryClient


def _run_git(args, cwd):
    subprocess.run(["git", *args], cwd=str(cwd), check=True, capture_output=True, text=True)


@pytest.fixture
def git_repo():
    repo_root = Path(tempfile.mkdtemp())
    _run_git(["init"], repo_root)
    _run_git(["config", "user.email", "test@example.com"], repo_root)
    _run_git(["config", "user.name", "Test"], repo_root)

    skill_dir = repo_root / "my-skill"
    src = skill_dir / "src"
    src.mkdir(parents=True)
    (src / "main.py").write_text("# placeholder")
    manifest = {
        "name": "my-skill",
        "version": "1.0.0",
        "description": "a test skill",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
    }
    (skill_dir / "skill.json").write_text(json.dumps(manifest))

    (repo_root / ".gitkeep").write_text("")
    _run_git(["add", "-A"], repo_root)
    _run_git(["commit", "-m", "add my-skill"], repo_root)

    yield repo_root, skill_dir
    shutil.rmtree(repo_root, ignore_errors=True)


@pytest.fixture
def registry(git_repo):
    repo_root, _ = git_repo
    reg_path = repo_root / "registry"
    return RegistryClient(reg_path, auto_tag=True)


class TestVerifyAgainstGit:
    def test_happy_path_matches(self, git_repo, registry):
        _, skill_dir = git_repo
        registry.publish(skill_dir)

        result = verify_against_git(registry, "my-skill")
        assert result["valid"] is True
        assert result["git_tag"] == "skill/my-skill/1.0.0"

    def test_no_git_tag_recorded(self, git_repo, registry):
        _, skill_dir = git_repo
        registry.publish(skill_dir, tag=False)

        result = verify_against_git(registry, "my-skill")
        assert result["valid"] is None
        assert result["reason"] == "no git tag recorded"

    def test_drift_detected_on_index_tamper(self, git_repo, registry):
        _, skill_dir = git_repo
        registry.publish(skill_dir)

        index = registry._load_index()
        index["skills"]["my-skill"]["ids"]["1.0.0"] = "skill://sha256/" + "0" * 64 + "/my-skill@1.0.0"
        registry._save_index(index)

        result = verify_against_git(registry, "my-skill")
        assert result["valid"] is False
        assert "Hash mismatch" in result["errors"][0]

    def test_unknown_skill(self, registry):
        result = verify_against_git(registry, "no-such-skill")
        assert result["valid"] is False
