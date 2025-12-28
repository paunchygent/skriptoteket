from __future__ import annotations

from skriptoteket.application.catalog.filtering import CatalogFilterService
from skriptoteket.domain.curated_apps.models import (
    CuratedAppDefinition,
    CuratedAppPlacement,
    curated_app_tool_id,
)
from skriptoteket.domain.identity.models import Role
from tests.fixtures.identity_fixtures import make_user


def _app(
    *,
    app_id: str,
    title: str,
    summary: str | None,
    min_role: Role,
    placements: list[CuratedAppPlacement],
) -> CuratedAppDefinition:
    return CuratedAppDefinition(
        app_id=app_id,
        tool_id=curated_app_tool_id(app_id=app_id),
        app_version="test",
        title=title,
        summary=summary,
        min_role=min_role,
        placements=placements,
    )


def test_filter_curated_apps_respects_role_and_search() -> None:
    service = CatalogFilterService()
    actor = make_user(role=Role.USER)

    allowed = _app(
        app_id="demo.allowed",
        title="Math Helper",
        summary="Do sums",
        min_role=Role.USER,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="matematik")],
    )
    blocked = _app(
        app_id="demo.admin",
        title="Admin Console",
        summary=None,
        min_role=Role.ADMIN,
        placements=[CuratedAppPlacement(profession_slug="larare", category_slug="matematik")],
    )

    result = service.filter_curated_apps(
        apps=[allowed, blocked],
        actor=actor,
        profession_slugs=None,
        category_slugs=None,
        search_term="math",
    )

    assert result == [allowed]


def test_filter_curated_apps_matches_combined_facets() -> None:
    service = CatalogFilterService()
    actor = make_user(role=Role.USER)

    app = _app(
        app_id="demo.multi",
        title="Multi",
        summary=None,
        min_role=Role.USER,
        placements=[
            CuratedAppPlacement(profession_slug="p1", category_slug="c1"),
            CuratedAppPlacement(profession_slug="p2", category_slug="c2"),
        ],
    )

    no_match = service.filter_curated_apps(
        apps=[app],
        actor=actor,
        profession_slugs=["p1"],
        category_slugs=["c2"],
        search_term=None,
    )
    assert no_match == []

    match = service.filter_curated_apps(
        apps=[app],
        actor=actor,
        profession_slugs=["p1"],
        category_slugs=["c1", "c2"],
        search_term=None,
    )
    assert match == [app]
