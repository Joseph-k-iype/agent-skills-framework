"""Three-tier RBAC catalog: roles, permission codes, role→permission mapping.

This is the single source of truth consumed by the seeder and by the
permission-enforcing FastAPI dependencies.
"""

from __future__ import annotations

from enum import StrEnum


class RoleName(StrEnum):
    CONSUMER = "consumer"
    DEVELOPER = "developer"
    ADMIN = "admin"


# Canonical permission codes (resource:action).
PERMISSIONS: dict[str, str] = {
    # workspace / folders
    "workspace:read": "View workspaces",
    "workspace:create": "Create workspaces",
    "workspace:update": "Update workspaces",
    "workspace:delete": "Delete workspaces",
    "folder:read": "View folders",
    "folder:create": "Create folders",
    "folder:update": "Update / move folders",
    "folder:delete": "Delete folders",
    # skills
    "skill:read": "View skills",
    "skill:create": "Create skills",
    "skill:update": "Update skills",
    "skill:delete": "Delete skills",
    "skill:publish": "Publish skills",
    "skill:clone": "Clone skills into a workspace",
    "skill:evaluate": "Run skill evaluations",
    # knowledge
    "okf:import": "Import OKF knowledge",
    "search:read": "Run semantic / graph search",
    # admin
    "admin:users": "Manage users",
    "admin:roles": "Manage roles & permissions",
    "admin:audit": "Read audit logs",
    "marketplace:moderate": "Moderate the marketplace",
}

_CONSUMER = {"workspace:read", "skill:read", "skill:clone", "search:read"}
_DEVELOPER = _CONSUMER | {
    "workspace:create",
    "workspace:update",
    "workspace:delete",
    "folder:read",
    "folder:create",
    "folder:update",
    "folder:delete",
    "skill:create",
    "skill:update",
    "skill:delete",
    "skill:publish",
    "skill:evaluate",
    "okf:import",
}
_ADMIN = set(PERMISSIONS.keys())  # everything

ROLE_PERMISSIONS: dict[str, set[str]] = {
    RoleName.CONSUMER: _CONSUMER,
    RoleName.DEVELOPER: _DEVELOPER,
    RoleName.ADMIN: _ADMIN,
}

ROLE_DESCRIPTIONS: dict[str, str] = {
    RoleName.CONSUMER: "Marketplace consumer — discover, search and clone skills",
    RoleName.DEVELOPER: "Authoring — workspaces, knowledge, skills, workflows",
    RoleName.ADMIN: "Enterprise control plane — full access",
}


def permissions_for(role: str) -> list[str]:
    return sorted(ROLE_PERMISSIONS.get(role, set()))
