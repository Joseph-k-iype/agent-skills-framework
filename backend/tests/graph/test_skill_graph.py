"""Integration tests for the skill graph repo against real FalkorDB."""

from __future__ import annotations

from app.repositories.skill_graph_repo import SkillGraphRepository
from app.repositories.workspace_graph_repo import WorkspaceGraphRepository

TS = "2026-01-01T00:00:00+00:00"


def _seed_folder() -> tuple[WorkspaceGraphRepository, str]:
    w = WorkspaceGraphRepository()
    w.create_workspace(id="w1", name="W", description=None, owner="u1", ts=TS)
    w.create_folder(id="fold1", name="Skills", path="/skills", workspace_id="w1", parent_id="w1", ts=TS)
    return w, "fold1"


def test_create_and_get_skill(graph_name):
    _seed_folder()
    r = SkillGraphRepository()
    s = r.create_skill(
        id="s1", skill_key="reporter-abc", name="Reporter", description="d", runtime="python",
        version="0.1.0", workspace_id="w1", folder_id="fold1", tags=[], capabilities=["x:y"], ts=TS,
    )
    assert s["status"] == "draft"
    got = r.get_skill("s1")
    assert got["name"] == "Reporter"
    assert got["is_current"] is True


def test_references_and_capabilities(graph_name):
    _seed_folder()
    r = SkillGraphRepository()
    r.create_skill(
        id="s1", skill_key="k", name="S", description=None, runtime="python", version="0.1.0",
        workspace_id="w1", folder_id="fold1", tags=[], capabilities=[], ts=TS,
    )
    # an OKF doc to reference
    from app.graph import client
    client.query("CREATE (:OKFDocument {id:'doc1', title:'Doc 1'})")
    r.set_references(id="s1", doc_ids=["doc1"])
    r.set_capabilities(id="s1", names=["reporting:revenue"], ts=TS)
    got = r.get_skill("s1")
    assert [ref["id"] for ref in got["references"]] == ["doc1"]
    assert got["capabilities"] == ["reporting:revenue"]


def test_version_lineage_carries_edges(graph_name):
    _seed_folder()
    r = SkillGraphRepository()
    r.create_skill(
        id="s1", skill_key="k", name="S", description=None, runtime="python", version="0.1.0",
        workspace_id="w1", folder_id="fold1", tags=[], capabilities=[], ts=TS,
    )
    from app.graph import client
    client.query("CREATE (:OKFDocument {id:'doc1', title:'Doc 1'})")
    r.set_references(id="s1", doc_ids=["doc1"])

    new = r.create_version(old_id="s1", new_id="s2", version="0.2.0", skill_key="k", ts=TS)
    assert new["version"] == "0.2.0"
    assert new["is_current"] is True

    chain = r.version_chain("k")
    assert [c["version"] for c in chain] == ["0.1.0", "0.2.0"]
    # only one current node
    assert sum(1 for c in chain if c["is_current"]) == 1
    # references carried to the new version
    assert [ref["id"] for ref in r.get_skill("s2")["references"]] == ["doc1"]


def test_clone_creates_independent_draft(graph_name):
    _seed_folder()
    r = SkillGraphRepository()
    r.create_skill(
        id="s1", skill_key="k", name="S", description="d", runtime="python", version="0.5.0",
        workspace_id="w1", folder_id="fold1", tags=["t"], capabilities=[], ts=TS,
    )
    clone = r.clone_skill(src_id="s1", new_id="s2", skill_key="k2", name="S copy", folder_id="fold1", ts=TS)
    assert clone["version"] == "0.1.0"
    assert clone["status"] == "draft"
    assert clone["skill_key"] == "k2"
