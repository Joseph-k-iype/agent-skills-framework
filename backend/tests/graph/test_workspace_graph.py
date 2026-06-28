"""Integration tests for the workspace/folder graph repo against real FalkorDB."""

from __future__ import annotations

from app.repositories.workspace_graph_repo import WorkspaceGraphRepository

TS = "2026-01-01T00:00:00+00:00"


def _repo() -> WorkspaceGraphRepository:
    return WorkspaceGraphRepository()


def test_create_and_fetch_workspace(graph_name):
    r = _repo()
    ws = r.create_workspace(id="w1", name="Finance", description="d", owner="u1", ts=TS)
    assert ws["id"] == "w1"
    assert r.get_workspace("w1")["name"] == "Finance"
    assert any(w["id"] == "w1" for w in r.list_workspaces(owner="u1", is_admin=False))


def test_folder_hierarchy_and_subtree(graph_name):
    r = _repo()
    r.create_workspace(id="w1", name="Finance", description=None, owner="u1", ts=TS)
    r.create_folder(id="f1", name="Reports", path="/reports", workspace_id="w1", parent_id="w1", ts=TS)
    r.create_folder(
        id="f2", name="Quarterly", path="/reports/quarterly", workspace_id="w1", parent_id="f1", ts=TS
    )

    subtree = r.get_subtree("w1")
    by_id = {f["id"]: f for f in subtree}
    assert by_id["f1"]["parent_id"] == "w1"
    assert by_id["f2"]["parent_id"] == "f1"

    children = r.get_children("f1")
    assert [c["id"] for c in children] == ["f2"]


def test_cycle_detection(graph_name):
    r = _repo()
    r.create_workspace(id="w1", name="W", description=None, owner="u1", ts=TS)
    r.create_folder(id="f1", name="A", path="/a", workspace_id="w1", parent_id="w1", ts=TS)
    r.create_folder(id="f2", name="B", path="/a/b", workspace_id="w1", parent_id="f1", ts=TS)

    # f2 is a descendant of f1 -> moving f1 under f2 must be blocked
    assert r.is_descendant(id="f1", target_id="f2") is True
    # f1 is not a descendant of f2
    assert r.is_descendant(id="f2", target_id="w1") is False


def test_move_reparents(graph_name):
    r = _repo()
    r.create_workspace(id="w1", name="W", description=None, owner="u1", ts=TS)
    r.create_folder(id="f1", name="A", path="/a", workspace_id="w1", parent_id="w1", ts=TS)
    r.create_folder(id="f2", name="B", path="/b", workspace_id="w1", parent_id="w1", ts=TS)
    r.create_folder(id="f3", name="C", path="/a/c", workspace_id="w1", parent_id="f1", ts=TS)

    r.move_folder(id="f3", new_parent_id="f2", ts=TS)
    assert r.get_parent("f3")["id"] == "f2"


def test_delete_folder_cascades(graph_name):
    r = _repo()
    r.create_workspace(id="w1", name="W", description=None, owner="u1", ts=TS)
    r.create_folder(id="f1", name="A", path="/a", workspace_id="w1", parent_id="w1", ts=TS)
    r.create_folder(id="f2", name="B", path="/a/b", workspace_id="w1", parent_id="f1", ts=TS)

    r.delete_folder("f1")
    assert r.get_folder("f1") is None
    assert r.get_folder("f2") is None
