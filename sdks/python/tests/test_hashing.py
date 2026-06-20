import hashlib
import json
import tempfile
from pathlib import Path

import pytest

from skill_sdk.hashing import (
    compute_skill_id,
    validate_skill_id,
    hash_from_skill_id,
    name_version_from_skill_id,
)


@pytest.fixture
def minimal_manifest():
    return {
        "name": "test-skill",
        "version": "1.0.0",
        "runtime": "python",
        "api_version": 1,
        "entry": "src/main.py",
    }


@pytest.fixture
def skill_root(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    src = tmp / "src"
    src.mkdir()
    main = src / "main.py"
    main.write_text("# placeholder")
    manifest_path = tmp / "skill.json"
    manifest_path.write_text(json.dumps(minimal_manifest))
    return tmp


def test_compute_skill_id_format(minimal_manifest, skill_root):
    skill_id = compute_skill_id(minimal_manifest, skill_root)
    assert skill_id.startswith("skill://sha256/")
    parts = skill_id.split("/")
    assert len(parts) == 5
    assert parts[3] == "test-skill@1.0.0" or parts[4] == "test-skill@1.0.0"


def test_compute_skill_id_deterministic(minimal_manifest, skill_root):
    id1 = compute_skill_id(minimal_manifest, skill_root)
    id2 = compute_skill_id(minimal_manifest, skill_root)
    assert id1 == id2


def test_compute_skill_id_changes_with_code(minimal_manifest, skill_root):
    id1 = compute_skill_id(minimal_manifest, skill_root)
    main_py = skill_root / "src" / "main.py"
    main_py.write_text("# changed content")
    id2 = compute_skill_id(minimal_manifest, skill_root)
    assert id1 != id2


def test_compute_skill_id_changes_with_manifest(minimal_manifest, skill_root):
    id1 = compute_skill_id(minimal_manifest, skill_root)
    minimal_manifest["description"] = "added description"
    id2 = compute_skill_id(minimal_manifest, skill_root)
    assert id1 != id2


def test_compute_skill_id_excludes_id_field(minimal_manifest, skill_root):
    minimal_manifest["id"] = "skill://sha256/abc123/test-skill@1.0.0"
    id1 = compute_skill_id(minimal_manifest, skill_root)
    del minimal_manifest["id"]
    id2 = compute_skill_id(minimal_manifest, skill_root)
    assert id1 == id2


def test_compute_skill_id_ignores_pycache(minimal_manifest, skill_root):
    id1 = compute_skill_id(minimal_manifest, skill_root)
    cache = skill_root / "__pycache__"
    cache.mkdir()
    (cache / "cached.pyc").write_text("xxx")
    id2 = compute_skill_id(minimal_manifest, skill_root)
    assert id1 == id2


def test_validate_skill_id_valid(minimal_manifest, skill_root):
    skill_id = compute_skill_id(minimal_manifest, skill_root)
    minimal_manifest["id"] = skill_id
    errors = validate_skill_id(minimal_manifest, skill_root)
    assert errors == []


def test_validate_skill_id_mismatch(minimal_manifest, skill_root):
    minimal_manifest["id"] = "skill://sha256/1234567890abcdef1234567890abcdef1234567890abcdef1234567890abcdef/test-skill@1.0.0"
    errors = validate_skill_id(minimal_manifest, skill_root)
    assert len(errors) == 1
    assert "mismatch" in errors[0]


def test_validate_skill_id_missing(minimal_manifest, skill_root):
    errors = validate_skill_id(minimal_manifest, skill_root)
    assert len(errors) == 1
    assert "Missing" in errors[0]


def test_hash_from_skill_id():
    sid = "skill://sha256/abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890/my-skill@1.0.0"
    h = hash_from_skill_id(sid)
    assert h == "abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"


def test_name_version_from_skill_id():
    sid = "skill://sha256/abc123/my-skill@2.0.0"
    name, ver = name_version_from_skill_id(sid)
    assert name == "my-skill"
    assert ver == "2.0.0"


def test_empty_source_dir(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    skill_id = compute_skill_id(minimal_manifest, tmp)
    assert skill_id.startswith("skill://sha256/")
    assert "test-skill@1.0.0" in skill_id


def test_unicode_content(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    (tmp / "data.txt").write_text("héllo wörld 🔥", encoding="utf-8")
    skill_id = compute_skill_id(minimal_manifest, tmp)
    assert skill_id.startswith("skill://sha256/")


def test_large_source_tree(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    for i in range(100):
        (tmp / f"file_{i}.py").write_text(f"# file {i}\n" * 10)
    skill_id = compute_skill_id(minimal_manifest, tmp)
    assert skill_id.startswith("skill://sha256/")


def test_dotfiles_ignored(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    id1 = compute_skill_id(minimal_manifest, tmp)
    (tmp / ".secret").write_text("sensitive")
    id2 = compute_skill_id(minimal_manifest, tmp)
    assert id1 == id2


# --- regression tests for the reworked hashing contract -------------------

def _write(root: Path, rel: str, content) -> None:
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(content, bytes):
        p.write_bytes(content)
    else:
        p.write_text(content, encoding="utf-8")


def test_tests_dir_excluded_from_hash(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "src/main.py", "print('x')")
    id1 = compute_skill_id(minimal_manifest, tmp)
    _write(tmp, "tests/test_main.py", "def test_x(): assert True")
    id2 = compute_skill_id(minimal_manifest, tmp)
    assert id1 == id2, "editing/adding tests must not change the skill id"


def test_top_level_test_files_excluded(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "src/main.py", "print('x')")
    id1 = compute_skill_id(minimal_manifest, tmp)
    _write(tmp, "test_thing.py", "def test_t(): pass")
    _write(tmp, "thing_test.py", "def test_t(): pass")
    _write(tmp, "conftest.py", "import pytest")
    _write(tmp, "ui.test.ts", "it('x', () => {})")
    id2 = compute_skill_id(minimal_manifest, tmp)
    assert id1 == id2


def test_non_allowlisted_files_are_hashed(minimal_manifest):
    # Previously only an extension allowlist was hashed; a shipped .sh/.txt was
    # silently outside the integrity boundary. They must now affect the id.
    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "src/main.py", "print('x')")
    id1 = compute_skill_id(minimal_manifest, tmp)
    _write(tmp, "scripts/install.sh", "#!/bin/sh\necho hi\n")
    id2 = compute_skill_id(minimal_manifest, tmp)
    assert id1 != id2


def test_binary_asset_is_hashed(minimal_manifest):
    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "src/main.py", "x")
    id1 = compute_skill_id(minimal_manifest, tmp)
    _write(tmp, "assets/logo.png", bytes(range(256)) * 8)
    id2 = compute_skill_id(minimal_manifest, tmp)
    assert id1 != id2


def test_nested_paths_use_posix_separator(minimal_manifest):
    # Guard against regressing to str(path), which embeds OS separators and
    # makes the id differ between Windows and POSIX. Recompute the expected
    # digest using forward slashes explicitly.
    import hashlib, json
    from skill_sdk.hashing import iter_source_files

    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "src/sub/deep/mod.py", "value = 1")

    h = hashlib.sha256()
    h.update(
        json.dumps(
            minimal_manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
    )
    for f in iter_source_files(tmp):
        rel = f.relative_to(tmp.resolve())
        assert "\\" not in rel.as_posix()
        h.update(rel.as_posix().encode("utf-8"))
        h.update(b"\x00")
        h.update(f.read_bytes())
        h.update(b"\x00")
    expected = f"skill://sha256/{h.hexdigest()}/test-skill@1.0.0"
    assert compute_skill_id(minimal_manifest, tmp) == expected


def test_prerelease_version_in_id(minimal_manifest):
    minimal_manifest["version"] = "1.0.0-rc.1"
    tmp = Path(tempfile.mkdtemp())
    _write(tmp, "main.py", "x")
    sid = compute_skill_id(minimal_manifest, tmp)
    from skill_sdk.hashing import name_version_from_skill_id
    name, ver = name_version_from_skill_id(sid)
    assert name == "test-skill"
    assert ver == "1.0.0-rc.1"
