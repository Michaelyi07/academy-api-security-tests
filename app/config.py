"""Environment-only configuration. No secrets are stored in source."""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    database_url: str = os.environ.get(
        "ACADEMY_DATABASE_URL",
        "postgresql+psycopg://postgres@127.0.0.1:5433/academy_scope_test",
    )
    # Trusted identity gateway header names (S2-IAM stub). In production these
    # are injected by the IAM sidecar; here tests set them explicitly.
    header_org: str = "X-Org-Id"
    header_site: str = "X-Site-Id"
    header_user: str = "X-User-Id"
    header_roles: str = "X-User-Roles"
    header_contact: str = "X-Contact-Id"


def get_settings() -> Settings:
    return Settings()
