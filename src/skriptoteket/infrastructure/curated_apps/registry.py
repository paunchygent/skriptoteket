from __future__ import annotations

from uuid import UUID

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol


class InMemoryCuratedAppRegistry(CuratedAppRegistryProtocol):
    def __init__(self, *, settings: Settings) -> None:
        app_id = "demo.counter"
        app = CuratedAppDefinition(
            app_id=app_id,
            tool_id=curated_app_tool_id(app_id=app_id),
            app_version=f"app:{settings.APP_VERSION}",
            title="Interaktiv räknare (curated)",
            summary="Demo-app som körs utan verktygseditor och använder UI-kontrakt v2.",
            min_role=Role.USER,
            placements=[
                CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
            ],
        )

        self._apps = [app]
        self._apps_by_id: dict[str, CuratedAppDefinition] = {app.app_id: app for app in self._apps}
        self._apps_by_tool_id: dict[UUID, CuratedAppDefinition] = {
            app.tool_id: app for app in self._apps
        }

    def list_all(self) -> list[CuratedAppDefinition]:
        return list(self._apps)

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._apps_by_id.get(app_id.strip())

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        return self._apps_by_tool_id.get(tool_id)

