import tempfile
from pathlib import Path

import pytest

from skill_sdk.sources import LocalSource, GitSource, create_source


@pytest.fixture
def local_skills_dir():
    tmp = Path(tempfile.mkdtemp())
    skill_dir = tmp / "my-skill-1.0.0"
    skill_dir.mkdir()
    (skill_dir / "main.py").write_text("# placeholder")
    (skill_dir / "skill.yaml").write_text("name: my-skill\nversion: 1.0.0\n")
    return tmp


def test_local_source_list(local_skills_dir):
    src = LocalSource(local_skills_dir)
    skills = src.list_skills()
    assert "my-skill" in skills


def test_local_source_list_empty():
    tmp = Path(tempfile.mkdtemp())
    src = LocalSource(tmp)
    assert src.list_skills() == {}


def test_local_source_fetch(local_skills_dir):
    src = LocalSource(local_skills_dir)
    target = Path(tempfile.mkdtemp()) / "skills"
    target.mkdir()
    result = src.fetch("my-skill", "1.0.0", target)
    assert result.exists()
    assert (result / "main.py").exists()


def test_local_source_fetch_not_found(local_skills_dir):
    src = LocalSource(local_skills_dir)
    target = Path(tempfile.mkdtemp()) / "skills"
    target.mkdir()
    with pytest.raises(FileNotFoundError):
        src.fetch("nonexistent", "1.0.0", target)


def test_git_source_requires_url():
    src = GitSource(url="https://example.com/repo.git")
    assert src.type == "git"
    assert src.url == "https://example.com/repo.git"


def test_git_source_list_empty():
    src = GitSource(url="https://example.com/nonexistent.git")
    assert src.list_skills() == {}


def test_create_source_local():
    config = {"type": "local", "path": "/tmp/test"}
    src = create_source(config)
    assert isinstance(src, LocalSource)
    assert src.type == "local"


def test_create_source_git():
    config = {"type": "git", "url": "https://example.com/repo.git"}
    src = create_source(config)
    assert isinstance(src, GitSource)
    assert src.type == "git"


def test_create_source_unknown():
    config = {"type": "s3"}
    with pytest.raises(ValueError, match="Unknown source type"):
        create_source(config)


def test_local_source_latest_is_semver_max():
    tmp = Path(tempfile.mkdtemp())
    for v in ("0.9.0", "0.10.0", "0.2.0"):
        d = tmp / f"my-skill-{v}"
        d.mkdir()
        (d / "skill.yaml").write_text(f"name: my-skill\nversion: {v}\n")
    src = LocalSource(tmp)
    skills = src.list_skills()
    # Lexical max would be "0.9.0"; correct SemVer max is "0.10.0".
    assert skills["my-skill"]["latest"] == "0.10.0"
    assert set(skills["my-skill"]["versions"]) == {"0.9.0", "0.10.0", "0.2.0"}


def test_local_source_hyphenated_name_and_prerelease():
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data-discovery-1.0.0-rc.1").mkdir()
    (tmp / "data-discovery-1.0.0-rc.1" / "skill.yaml").write_text("name: data-discovery\n")
    src = LocalSource(tmp)
    skills = src.list_skills()
    assert "data-discovery" in skills
    assert "1.0.0-rc.1" in skills["data-discovery"]["versions"]


def test_local_source_ignores_dot_dirs():
    tmp = Path(tempfile.mkdtemp())
    (tmp / ".git").mkdir()
    (tmp / "good-1.0.0").mkdir()
    (tmp / "good-1.0.0" / "skill.yaml").write_text("name: good\n")
    src = LocalSource(tmp)
    assert set(src.list_skills().keys()) == {"good"}


def test_create_source_local_missing_path():
    with pytest.raises(ValueError, match="requires a 'path'"):
        create_source({"type": "local"})


def test_create_source_git_missing_url():
    with pytest.raises(ValueError, match="requires a 'url'"):
        create_source({"type": "git"})
