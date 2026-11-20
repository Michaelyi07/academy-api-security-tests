"""S2-IAM stub: identity, roles, 11 academy permission points, and data scope.

In production the gateway injects trusted identity headers. Here the test
suite sets them explicitly; no real authentication or personal data is used.
"""
from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from fastapi import Depends, Header, HTTPException, Request

from .config import Settings, get_settings

# --- 11 academy permission points -----------------------------------------
PERMISSION_POINTS: tuple[str, ...] = (
    "academy.course.view",
    "academy.course.manage",
    "academy.session.view",
    "academy.session.manage",
    "academy.roster.view",
    "academy.roster.manage",
    "academy.review.view",
    "academy.review.moderate",
    "academy.learning.view",
    "academy.registration.view",
    "academy.mobile.reveal",
)

ROLES: tuple[str, ...] = (
    "platform_admin",
    "org_admin",
    "club_admin",
    "club_employee",
    "membership_manager",
    "member",
)

_ROLE_GRANTS: dict[str, frozenset[str]] = {
    "platform_admin": frozenset(PERMISSION_POINTS),
    "org_admin": frozenset(p for p in PERMISSION_POINTS if p != "academy.mobile.reveal"),
    "club_admin": frozenset(
        p for p in PERMISSION_POINTS if p not in ("academy.mobile.reveal",)
    ),
    "club_employee": frozenset(
        (
            "academy.course.view",
            "academy.session.view",
            "academy.roster.view",
            "academy.review.view",
            "academy.learning.view",
            "academy.registration.view",
        )
    ),
    "membership_manager": frozenset(
        (
            "academy.course.view",
            "academy.session.view",
            "academy.roster.view",
            "academy.learning.view",
            "academy.registration.view",
        )
    ),
    "member": frozenset(),  # no admin-side permission points
}


def grants_for(role: str) -> frozenset[str]:
    return _ROLE_GRANTS[role]


@dataclass(frozen=True)
class Identity:
    user_id: UUID
    org_id: UUID
    site_id: UUID
    roles: frozenset[str]
    contact_id: UUID | None = None

    def has(self, permission: str) -> bool:
        return any(permission in _ROLE_GRANTS.get(r, frozenset()) for r in self.roles)


def get_identity(
    request: Request,
    settings: Settings = Depends(get_settings),
    x_org_id: str | None = Header(default=None, alias="X-Org-Id"),
    x_site_id: str | None = Header(default=None, alias="X-Site-Id"),
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_roles: str | None = Header(default=None, alias="X-User-Roles"),
    x_contact_id: str | None = Header(default=None, alias="X-Contact-Id"),
) -> Identity:
    """Resolve a trusted-gateway identity. Missing or malformed headers -> 400.

    Header names come from env-driven Settings so the integration point to the
    real S2-IAM gateway is a configuration change, not a code change.
    """
    missing = [
        name
        for name, value in (
            (settings.header_org, x_org_id),
            (settings.header_site, x_site_id),
            (settings.header_user, x_user_id),
            (settings.header_roles, x_user_roles),
        )
        if not value
    ]
    if missing:
        raise HTTPException(status_code=400, detail={"code": "missing_identity_headers", "headers": missing})
    try:
        roles = frozenset(r.strip() for r in (x_user_roles or "").split(",") if r.strip())
        unknown = roles - set(ROLES)
        if unknown:
            raise ValueError(f"unknown roles: {sorted(unknown)}")
        return Identity(
            user_id=UUID(x_user_id),  # type: ignore[arg-type]
            org_id=UUID(x_org_id),  # type: ignore[arg-type]
            site_id=UUID(x_site_id),  # type: ignore[arg-type]
            roles=roles,
            contact_id=UUID(x_contact_id) if x_contact_id else None,
        )
    except (ValueError, TypeError) as exc:
        raise HTTPException(status_code=400, detail={"code": "malformed_identity_headers", "reason": str(exc)})


def require(permission: str):
    """Dependency factory: 403 when the identity lacks the permission point."""

    def _dep(identity: Identity = Depends(get_identity)) -> Identity:
        if not identity.has(permission):
            raise HTTPException(status_code=403, detail={"code": "forbidden", "permission": permission})
        return identity

    return _dep


def admin_scope(identity: Identity) -> tuple[UUID, UUID | None]:
    """Return (org_id, site_id_or_None). Platform/org admins may see all sites
    in their org; club roles are locked to their own site."""
    broad = identity.roles & {"platform_admin", "org_admin"}
    return identity.org_id, None if broad else identity.site_id


def not_found() -> HTTPException:
    """Uniform 404 with no existence leak."""
    return HTTPException(status_code=404, detail={"code": "not_found"})
