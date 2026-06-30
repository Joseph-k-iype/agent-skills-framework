"""Import all models so Alembic autogenerate + Base.metadata see them."""

from app.models.api_key import ApiKey
from app.models.audit_log import AuditLog
from app.models.eval_run import EvalRun
from app.models.marketplace import MarketplaceListing
from app.models.notification import Notification
from app.models.organization import Organization
from app.models.permission import Permission
from app.models.role import Role, role_permissions
from app.models.session import Session
from app.models.skill_version import SkillVersion
from app.models.usage_event import UsageEvent
from app.models.user import User

__all__ = [
    "ApiKey",
    "AuditLog",
    "EvalRun",
    "MarketplaceListing",
    "Notification",
    "Organization",
    "Permission",
    "Role",
    "role_permissions",
    "Session",
    "SkillVersion",
    "UsageEvent",
    "User",
]
