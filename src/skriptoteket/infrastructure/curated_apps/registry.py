from __future__ import annotations

from uuid import UUID

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol


class InMemoryCuratedAppRegistry(CuratedAppRegistryProtocol):
    def __init__(self, *, settings: Settings) -> None:
        app_version = f"app:{settings.APP_VERSION}"
        apps: list[CuratedAppDefinition] = [
            CuratedAppDefinition(
                app_id="demo.counter",
                tool_id=curated_app_tool_id(app_id="demo.counter"),
                app_version=app_version,
                ui_mode=CuratedAppUiMode.GENERIC_OK,
                title="Interaktiv räknare (demo)",
                summary="Demo-app som körs utan verktygseditor och använder UI-kontrakt v2.",
                min_role=Role.USER,
                placements=[
                    CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
                ],
            ),
            CuratedAppDefinition(
                app_id="chemistry.reagent_prep_chef",
                tool_id=curated_app_tool_id(app_id="chemistry.reagent_prep_chef"),
                app_version=app_version,
                ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
                title="Reagensberedning",
                summary=(
                    "Räkna ut massa/volym för lösningar med hydrat- och renhetsstöd + "
                    "säkerhetsråd för ämnen i listan."
                ),
                min_role=Role.USER,
                placements=[
                    CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt"),
                ],
            ),
            CuratedAppDefinition(
                app_id="documents.conversion_hub",
                tool_id=curated_app_tool_id(app_id="documents.conversion_hub"),
                app_version=app_version,
                ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
                title="Konvertera dokument",
                summary=(
                    "Konvertera PDF/HTML/Markdown/DOCX via Sir Convert-a-Lot v2 "
                    "(batch + forhandsvisning)."
                ),
                min_role=Role.USER,
                placements=[
                    CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
                    CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt"),
                ],
            ),
        ]

        self._apps = apps
        self._apps_by_id = {app.app_id: app for app in apps}
        self._apps_by_tool_id = {app.tool_id: app for app in apps}

    def list_all(self) -> list[CuratedAppDefinition]:
        return list(self._apps)

    def get_by_app_id(self, *, app_id: str) -> CuratedAppDefinition | None:
        return self._apps_by_id.get(app_id.strip())

    def get_by_tool_id(self, *, tool_id: UUID) -> CuratedAppDefinition | None:
        return self._apps_by_tool_id.get(tool_id)
