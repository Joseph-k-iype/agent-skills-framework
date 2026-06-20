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
