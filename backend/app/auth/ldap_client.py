"""LDAP authentication seam.

A single Protocol defines the contract so the auth service never imports ldap3
directly. In development ``LDAP_ENABLED=false`` and only the dev-admin path is
used; tests inject a fake implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.config import settings
from app.core.logging import get_logger

log = get_logger("ldap")


@dataclass
class LdapIdentity:
    username: str
    full_name: str | None
    dn: str
    groups: list[str]


class LdapClient(Protocol):
    def authenticate(self, username: str, password: str) -> LdapIdentity | None:
        """Return the identity on success, or None on bad credentials."""
        ...


class DisabledLdapClient:
    """Used when LDAP is turned off — always declines (dev-admin path handles login)."""

    def authenticate(self, username: str, password: str) -> LdapIdentity | None:
        return None


class Ldap3Client:
    """Real LDAP via ldap3 — bind, locate the user, read group memberships."""

    def authenticate(self, username: str, password: str) -> LdapIdentity | None:  # pragma: no cover
        import ldap3

        server = ldap3.Server(settings.ldap_uri, get_info=ldap3.ALL)
        # Service-account bind to find the user DN.
        try:
            conn = ldap3.Connection(
                server,
                user=settings.ldap_bind_dn or None,
                password=settings.ldap_bind_password or None,
                auto_bind=True,
            )
        except Exception as exc:
            log.warning("ldap_service_bind_failed", error=str(exc))
            return None

        conn.search(
            settings.ldap_user_base_dn,
            f"(uid={username})",
            attributes=["cn", "memberOf"],
        )
        if not conn.entries:
            return None
        entry = conn.entries[0]
        user_dn = entry.entry_dn

        # Re-bind as the user to verify the password.
        try:
            user_conn = ldap3.Connection(server, user=user_dn, password=password, auto_bind=True)
            user_conn.unbind()
        except Exception:
            return None

        groups = [str(g).split(",")[0].split("=")[-1] for g in (entry.memberOf or [])]
        full_name = str(entry.cn) if "cn" in entry else None
        return LdapIdentity(username=username, full_name=full_name, dn=user_dn, groups=groups)


def get_ldap_client() -> LdapClient:
    return Ldap3Client() if settings.ldap_enabled else DisabledLdapClient()
