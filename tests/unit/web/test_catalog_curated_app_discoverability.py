"""Catalog route tests for curated app discoverability surfaces."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import AsyncMock, Mock

import pytest

from skriptoteket.application.catalog.queries import ListToolsByTagsResult
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    CuratedAppUiMode,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.catalog import ListToolsByTagsHandlerProtocol
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1 import catalog as catalog_api
from tests.fixtures.catalog_fixtures import make_category, make_profession
from tests.fixtures.identity_fixtures import make_user


def _unwrap_dishka(fn):
    return getattr(fn, "__dishka_orig_func__", fn)


@pytest.mark.asyncio
async def test_list_tools_includes_flunk_out_frenzy_for_matching_placement(
    now: datetime,
) -> None:
    profession = make_profession(slug="gemensamt", label="Gemensamt", now=now)
    category = make_category(slug="ovrigt", label="Övrigt", now=now)
    handler = AsyncMock(spec=ListToolsByTagsHandlerProtocol)
    handler.handle.return_value = ListToolsByTagsResult(
        profession=profession,
        category=category,
        tools=[],
        curated_apps=[],
    )

    app = CuratedAppDefinition(
        app_id="games.flunk_out_frenzy",
        tool_id=curated_app_tool_id(app_id="games.flunk_out_frenzy"),
        app_version="app:test",
        ui_mode=CuratedAppUiMode.BESPOKE_REQUIRED,
        title="Flunk-Out Frenzy",
        summary="Local browser pinball with future official high scores.",
        min_role=Role.USER,
        placements=[
            CuratedAppPlacement(profession_slug="gemensamt", category_slug="ovrigt"),
            CuratedAppPlacement(profession_slug="larare", category_slug="ovrigt"),
        ],
    )
    curated_apps = Mock(spec=CuratedAppRegistryProtocol)
    curated_apps.list_all.return_value = [app]

    response = await _unwrap_dishka(catalog_api.list_tools)(
        profession_slug="gemensamt",
        category_slug="ovrigt",
        handler=handler,
        curated_apps=curated_apps,
        user=make_user(role=Role.USER),
    )

    assert response.curated_apps
    assert response.curated_apps[0].app_id == "games.flunk_out_frenzy"
    assert response.curated_apps[0].title == "Flunk-Out Frenzy"
