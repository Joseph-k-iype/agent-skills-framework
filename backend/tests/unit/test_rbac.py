"""RBAC catalog invariants."""

from __future__ import annotations

from app.auth.rbac import PERMISSIONS, ROLE_PERMISSIONS, RoleName, permissions_for


def test_admin_has_every_permission():
    assert ROLE_PERMISSIONS[RoleName.ADMIN] == set(PERMISSIONS)


def test_role_hierarchy_is_monotonic():
    consumer = ROLE_PERMISSIONS[RoleName.CONSUMER]
    developer = ROLE_PERMISSIONS[RoleName.DEVELOPER]
    admin = ROLE_PERMISSIONS[RoleName.ADMIN]
    assert consumer <= developer <= admin


def test_all_role_permissions_are_known_codes():
    for perms in ROLE_PERMISSIONS.values():
        assert perms <= set(PERMISSIONS)


def test_consumer_cannot_author():
    assert "skill:create" not in permissions_for(RoleName.CONSUMER)
    assert "skill:create" in permissions_for(RoleName.DEVELOPER)
