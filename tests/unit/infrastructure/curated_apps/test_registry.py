"""Registry tests for competitive-game curated app discoverability."""

from __future__ import annotations

from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.models import CuratedAppUiMode, curated_app_tool_id
from skriptoteket.domain.identity.models import Role
from skriptoteket.infrastructure.curated_apps.registry import InMemoryCuratedAppRegistry


def test_registry_includes_flunk_out_frenzy_with_expected_identity() -> None:
    registry = InMemoryCuratedAppRegistry(
        settings=Settings(
            APP_VERSION="9.9.9",
            DATABASE_URL="postgresql+asyncpg://postgres:postgres@localhost:5432/test",
        )
    )

    app = registry.get_by_app_id(app_id="games.flunk_out_frenzy")

    assert app is not None
    assert app.app_id == "games.flunk_out_frenzy"
    assert app.tool_id == curated_app_tool_id(app_id="games.flunk_out_frenzy")
    assert app.app_version == "app:9.9.9"
    assert app.ui_mode is CuratedAppUiMode.BESPOKE_REQUIRED
    assert app.title == "Flunk-Out Frenzy"
    assert app.min_role is Role.USER
    assert app.matches_placement(profession_slug="gemensamt", category_slug="ovrigt") is True
    assert app.matches_placement(profession_slug="larare", category_slug="ovrigt") is True
