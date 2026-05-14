"""Shared helpers for public curated-app web routes.

Purpose:
  Centralize the fail-closed public-access checks shared by the public host
  bootstrap route and later public helper namespaces.

Relationships:
  - Reads the canonical registry-owned `public_access_profile`.
  - Raises the same not-found contract used by authenticated/public app hosts.
"""

from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPublicCapability,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol


def require_public_curated_app(
    *, app_id: str, registry: CuratedAppRegistryProtocol
) -> CuratedAppDefinition:
    """Return the public app definition or fail closed."""

    app = registry.get_by_app_id(app_id=app_id)
    if app is None or not app.supports_public_access:
        raise not_found("CuratedApp", app_id)
    return app


def require_public_curated_app_capability(
    *, app_id: str, scope: str, registry: CuratedAppRegistryProtocol
) -> tuple[CuratedAppDefinition, CuratedAppPublicCapability]:
    """Return a scoped public app capability or fail closed."""

    app = registry.get_by_app_id(app_id=app_id)
    if app is None:
        raise not_found("CuratedApp", app_id)

    capability = app.get_public_capability(scope=scope)
    if capability is None:
        raise not_found("CuratedAppPublicCapability", f"{app_id}:{scope}")
    return app, capability
