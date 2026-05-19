"""Conversion Hub API access helpers.

Purpose:
  Share the authenticated Conversion Hub app-id and role gate across bespoke
  route modules without duplicating authorization checks.

Relationships:
  - Used by Conversion Hub job/artifact routes.
  - Used by Exam Converter correction-session routes under the same app.
"""

from __future__ import annotations

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.identity.role_guards import require_at_least_role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol

APP_ID = "documents.conversion_hub"


def require_conversion_hub_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    """Require that the actor can access the Conversion Hub curated app."""

    app = registry.get_by_app_id(app_id=APP_ID)
    if app is None:
        raise not_found("CuratedApp", APP_ID)
    require_at_least_role(user=user, role=app.min_role)
