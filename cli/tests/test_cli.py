import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from cli.src.main import cmd_init, cmd_validate, cmd_list, cmd_info, cmd_doc, cmd_evaluate


class TestInitCommand:
    @pytest.fixture
    def args(self):
        class FakeArgs:
            name = "test-skill"
            path = None
            registry = None
        return FakeArgs()

    def test_init_creates_skill(self, args, tmp_path):
        args.path = str(tmp_path / "test-skill")
        cmd_init(args)
        skill_dir = Path(args.path)
        assert (skill_dir / "SKILL.md").exists()
        assert (skill_dir / "src" / "main.py").exists()
        assert (skill_dir / "tests").exists()

    def test_init_creates_valid_manifest(self, args, tmp_path):
        args.path = str(tmp_path / "test-skill")
        cmd_init(args)
        from skill_sdk.validation import load_manifest
        manifest = load_manifest(Path(args.path) / "SKILL.md")
        assert manifest["name"] == "test-skill"
        assert manifest["version"] == "0.1.0"
        assert manifest["runtime"] == "python"
        assert manifest["entry"] == "src/main.py"

    def test_init_fails_on_existing(self, args, tmp_path):
        args.path = str(tmp_path / "existing")
        Path(args.path).mkdir()
        with pytest.raises(SystemExit):
            cmd_init(args)


class TestValidateCommand:
    @pytest.fixture
    def valid_skill(self, tmp_path):
        manifest = {
            "name": "valid-skill", "version": "1.0.0", "description": "test skill",
            "runtime": "python", "api_version": 1, "entry": "main.py",
        }
        (tmp_path / "skill.json").write_text(json.dumps(manifest))
        (tmp_path / "main.py").write_text("# placeholder")
        (tmp_path / "tests").mkdir()
        return tmp_path

    def test_validate_valid(self, valid_skill):
        class Args:
            path = str(valid_skill)
            registry = None
            deep = False
        cmd_validate(Args())

    def test_validate_invalid(self, tmp_path):
        (tmp_path / "skill.json").write_text('{"name": "incomplete"}')
        class Args:
            path = str(tmp_path)
            registry = None
            deep = False
        with pytest.raises(SystemExit):
            cmd_validate(Args())

    def test_validate_no_manifest(self, tmp_path):
        class Args:
            path = str(tmp_path)
            registry = None
            deep = False
        with pytest.raises(SystemExit):
            cmd_validate(Args())


class TestEvaluateCommand:
    @pytest.fixture
    def valid_skill(self, tmp_path):
        manifest = {
            "name": "valid-skill", "version": "1.0.0", "description": "test skill",
            "runtime": "python", "api_version": 1, "entry": "main.py",
        }
        (tmp_path / "skill.json").write_text(json.dumps(manifest))
        (tmp_path / "main.py").write_text("# placeholder")
        (tmp_path / "tests").mkdir()
        return tmp_path

    def test_evaluate_exits_zero_with_no_judge_configured(self, valid_skill, tmp_path, monkeypatch, capsys):
        # Without this, an ambient repo-root .env with SKILLS_EVAL_MODEL set would
        # make this hit a real provider over the network instead of testing the
        # no-judge-configured degradation path it's named for.
        monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
        monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
        class Args:
            path = str(valid_skill)
            judge = None
            format = "json"
            registry = str(tmp_path / "registry")
        cmd_evaluate(Args())
        out = json.loads(capsys.readouterr().out)
        assert out["judge_status"] == "skipped"

    def test_evaluate_judge_none_skips_explicitly(self, valid_skill, tmp_path, capsys):
        class Args:
            path = str(valid_skill)
            judge = "none"
            format = "json"
            registry = str(tmp_path / "registry")
        cmd_evaluate(Args())
        out = json.loads(capsys.readouterr().out)
        assert out["judge_status"] == "skipped"
        assert "disabled" in out["judge_skip_reason"]

    def test_evaluate_exits_nonzero_on_structural_errors(self, tmp_path, monkeypatch):
        # Structural errors don't skip the agentic pass, so without stubbing this
        # would also hit a real provider via the ambient repo-root .env.
        monkeypatch.setattr("dotenv.load_dotenv", lambda *a, **k: False)
        monkeypatch.delenv("SKILLS_EVAL_MODEL", raising=False)
        (tmp_path / "skill.json").write_text('{"name": "incomplete"}')
        class Args:
            path = str(tmp_path)
            judge = None
            format = "markdown"
            registry = str(tmp_path / "registry")
        with pytest.raises(SystemExit):
            cmd_evaluate(Args())

    def test_evaluate_no_manifest_exits_nonzero(self, tmp_path):
        class Args:
            path = str(tmp_path)
            judge = None
            format = "markdown"
            registry = str(tmp_path / "registry")
        with pytest.raises(SystemExit):
            cmd_evaluate(Args())


class TestListCommand:
    def test_list_empty(self):
        tmp = Path(tempfile.mkdtemp())
        from skill_sdk.registry import RegistryClient
        rc = RegistryClient(tmp, auto_tag=False)
        rc._save_index({"schema_version": 1, "sources": [], "skills": {}})

        class Args:
            registry = str(tmp)
        cmd_list(Args())

    def test_list_with_skills(self, tmp_path):
        from skill_sdk.registry import RegistryClient
        rc = RegistryClient(tmp_path, auto_tag=False)
        rc._save_index({
            "schema_version": 1,
            "sources": [],
            "skills": {
                "skill-a": {"latest": "1.0.0", "versions": ["1.0.0"], "ids": {"1.0.0": "abc"}, "locations": {}},
                "skill-b": {"latest": "2.0.0", "versions": ["1.0.0", "2.0.0"], "ids": {}, "locations": {}},
            },
        })
        class Args:
            registry = str(tmp_path)
        cmd_list(Args())


class TestInfoCommand:
    def test_info_not_found(self, tmp_path):
        class Args:
            name = "ghost"
            registry = str(tmp_path)
        with pytest.raises(SystemExit):
            cmd_info(Args())


class TestDocCommand:
    @pytest.fixture
    def skill_manifest(self, tmp_path):
        manifest = {
            "name": "doc-skill", "version": "1.0.0", "runtime": "python",
            "api_version": 1, "entry": "main.py",
            "description": "Test skill for doc generation",
            "triggers": {"events": ["data.updated"], "commands": ["/run"]},
            "capabilities": ["doc:test"],
            "permissions": [{"resource": "api", "actions": ["read"]}],
        }
        (tmp_path / "skill.yaml").write_text(yaml.dump(manifest))
        (tmp_path / "main.py").write_text("# placeholder")
        return tmp_path

    def test_doc_generation(self, skill_manifest):
        class Args:
            path = str(skill_manifest)
            format = "markdown"
            output = str(skill_manifest / "README.md")
        cmd_doc(Args())
        assert (skill_manifest / "README.md").exists()
        content = (skill_manifest / "README.md").read_text()
        assert "# doc-skill v1.0.0" in content
        assert "doc:test" in content


class TestBuildCommand:
    @pytest.fixture
    def buildable_skill(self, tmp_path):
        manifest = {
            "name": "build-skill", "version": "1.0.0", "description": "test skill",
            "runtime": "python", "api_version": 1, "entry": "src/main.py",
        }
        (tmp_path / "src").mkdir()
        (tmp_path / "src" / "main.py").write_text("# entry")
        (tmp_path / "skill.json").write_text(json.dumps(manifest))
        (tmp_path / ".env").write_text("SECRET=x")
        return tmp_path

    def _args(self, path):
        class Args:
            pass
        a = Args()
        a.path = str(path)
        a.registry = None
        a.skip_validation = False
        return a

    def test_build_stamps_id_into_dist_manifest(self, buildable_skill):
        from cli.src.main import cmd_build
        cmd_build(self._args(buildable_skill))
        dist_manifest = json.loads((buildable_skill / "dist" / "skill.json").read_text())
        # Regression: the copy loop used to overwrite the stamped manifest with
        # the id-less source, leaving the built artifact without its id.
        assert dist_manifest.get("id", "").startswith("skill://sha256/")

    def test_build_excludes_dotenv_from_dist(self, buildable_skill):
        from cli.src.main import cmd_build
        cmd_build(self._args(buildable_skill))
        assert not (buildable_skill / "dist" / ".env").exists()


def test_evaluate_markdown_renders_agent_execution_section(capsys):
    from skill_sdk.evaluation.state import (
        AgentExecutionSummary, ConfigAggregate, EvaluationReport)
    # import the renderer used by cmd_evaluate (adjust name to the actual function)
    from cli.src.main import _render_eval_markdown  # noqa
    report = EvaluationReport(skill_name="s", skill_version="1.0.0", run_at="t",
                              judge_status="ok", judge_skip_reason=None)
    report.agent_execution = AgentExecutionSummary(
        comparison_mode="with_without", skip_reason=None, runs_per_case=1,
        with_skill=ConfigAggregate(pass_rate_mean=0.9),
        baseline=ConfigAggregate(pass_rate_mean=0.3),
        delta={"pass_rate": 0.6, "tokens": 1200.0, "duration": 8000.0}, cases=[])
    text = _render_eval_markdown(report)
    assert "Agent execution" in text
    assert "with_without" in text
    assert "0.6" in text  # delta pass_rate
