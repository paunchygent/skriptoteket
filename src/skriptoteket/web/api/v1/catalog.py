"""Catalog API endpoints for SPA browse views (ST-11-06)."""

from typing import Literal
from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.catalog.queries import (
    CatalogItemKind,
    ListAllCategoriesQuery,
    ListAllToolsQuery,
    ListCategoriesForProfessionQuery,
    ListProfessionsQuery,
    ListToolsByTagsQuery,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.catalog import (
    ListAllCategoriesHandlerProtocol,
    ListAllToolsHandlerProtocol,
    ListCategoriesForProfessionHandlerProtocol,
    ListProfessionsHandlerProtocol,
    ListToolsByTagsHandlerProtocol,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


def _parse_slug_list(value: str | None) -> list[str] | None:
    if value is None:
        return None
    slugs = [part.strip().lower() for part in value.split(",") if part.strip()]
    return slugs or None


def _parse_search_term(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


class ProfessionItem(BaseModel):
    """Profession for API responses."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    label: str
    sort_order: int


class CategoryItem(BaseModel):
    """Category for API responses."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    label: str


class ListProfessionsResponse(BaseModel):
    """Response for listing all professions."""

    model_config = ConfigDict(frozen=True)

    professions: list[ProfessionItem]


class ListAllCategoriesResponse(BaseModel):
    """Response for listing all categories (unfiltered)."""

    model_config = ConfigDict(frozen=True)

    categories: list[CategoryItem]


class ListCategoriesResponse(BaseModel):
    """Response for listing categories within a profession."""

    model_config = ConfigDict(frozen=True)

    profession: ProfessionItem
    categories: list[CategoryItem]


class ToolItem(BaseModel):
    """Tool for API responses."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    slug: str
    title: str
    summary: str | None


class CuratedAppItem(BaseModel):
    """Curated app for API responses."""

    model_config = ConfigDict(frozen=True)

    app_id: str
    tool_id: UUID
    title: str
    summary: str | None
    min_role: Role


class ListToolsResponse(BaseModel):
    """Response for listing tools within a profession/category."""

    model_config = ConfigDict(frozen=True)

    profession: ProfessionItem
    category: CategoryItem
    tools: list[ToolItem]
    curated_apps: list[CuratedAppItem]


class CatalogToolItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["tool"]
    id: UUID
    slug: str
    title: str
    summary: str | None
    is_favorite: bool


class CatalogCuratedAppItem(BaseModel):
    model_config = ConfigDict(frozen=True)

    kind: Literal["curated_app"]
    id: UUID
    app_id: str
    title: str
    summary: str | None
    is_favorite: bool


class ListAllToolsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    items: list[CatalogToolItem | CatalogCuratedAppItem]
    professions: list[ProfessionItem]
    categories: list[CategoryItem]


@router.get("/professions", response_model=ListProfessionsResponse)
@inject
async def list_professions(
    handler: FromDishka[ListProfessionsHandlerProtocol],
    _user: User = Depends(require_user_api),
) -> ListProfessionsResponse:
    result = await handler.handle(ListProfessionsQuery())
    return ListProfessionsResponse(
        professions=[
            ProfessionItem(
                id=p.id,
                slug=p.slug,
                label=p.label,
                sort_order=p.sort_order,
            )
            for p in result.professions
        ]
    )


@router.get("/categories", response_model=ListAllCategoriesResponse)
@inject
async def list_all_categories(
    handler: FromDishka[ListAllCategoriesHandlerProtocol],
    _user: User = Depends(require_user_api),
) -> ListAllCategoriesResponse:
    result = await handler.handle(ListAllCategoriesQuery())
    return ListAllCategoriesResponse(
        categories=[
            CategoryItem(
                id=c.id,
                slug=c.slug,
                label=c.label,
            )
            for c in result.categories
        ]
    )


@router.get(
    "/professions/{profession_slug}/categories",
    response_model=ListCategoriesResponse,
)
@inject
async def list_categories(
    profession_slug: str,
    handler: FromDishka[ListCategoriesForProfessionHandlerProtocol],
    _user: User = Depends(require_user_api),
) -> ListCategoriesResponse:
    result = await handler.handle(ListCategoriesForProfessionQuery(profession_slug=profession_slug))
    return ListCategoriesResponse(
        profession=ProfessionItem(
            id=result.profession.id,
            slug=result.profession.slug,
            label=result.profession.label,
            sort_order=result.profession.sort_order,
        ),
        categories=[
            CategoryItem(
                id=c.id,
                slug=c.slug,
                label=c.label,
            )
            for c in result.categories
        ],
    )


@router.get(
    "/professions/{profession_slug}/categories/{category_slug}/tools",
    response_model=ListToolsResponse,
)
@inject
async def list_tools(
    profession_slug: str,
    category_slug: str,
    handler: FromDishka[ListToolsByTagsHandlerProtocol],
    curated_apps: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_user_api),
) -> ListToolsResponse:
    result = await handler.handle(
        actor=user,
        query=ListToolsByTagsQuery(
            profession_slug=profession_slug,
            category_slug=category_slug,
        ),
    )
    curated = [
        app
        for app in curated_apps.list_all()
        if app.matches_placement(
            profession_slug=profession_slug,
            category_slug=category_slug,
        )
    ]
    return ListToolsResponse(
        profession=ProfessionItem(
            id=result.profession.id,
            slug=result.profession.slug,
            label=result.profession.label,
            sort_order=result.profession.sort_order,
        ),
        category=CategoryItem(
            id=result.category.id,
            slug=result.category.slug,
            label=result.category.label,
        ),
        tools=[
            ToolItem(
                id=t.id,
                slug=t.slug,
                title=t.title,
                summary=t.summary,
            )
            for t in result.tools
        ],
        curated_apps=[
            CuratedAppItem(
                app_id=app.app_id,
                tool_id=app.tool_id,
                title=app.title,
                summary=app.summary,
                min_role=app.min_role,
            )
            for app in curated
        ],
    )


@router.get("/tools", response_model=ListAllToolsResponse)
@inject
async def list_all_tools(
    handler: FromDishka[ListAllToolsHandlerProtocol],
    user: User = Depends(require_user_api),
    professions: str | None = None,
    categories: str | None = None,
    q: str | None = None,
) -> ListAllToolsResponse:
    result = await handler.handle(
        actor=user,
        query=ListAllToolsQuery(
            profession_slugs=_parse_slug_list(professions),
            category_slugs=_parse_slug_list(categories),
            search_term=_parse_search_term(q),
        ),
    )
    items: list[CatalogToolItem | CatalogCuratedAppItem] = []
    for item in result.items:
        if item.kind is CatalogItemKind.TOOL:
            items.append(
                CatalogToolItem(
                    kind="tool",
                    id=item.id,
                    slug=item.slug or "",
                    title=item.title,
                    summary=item.summary,
                    is_favorite=item.is_favorite,
                )
            )
        else:
            items.append(
                CatalogCuratedAppItem(
                    kind="curated_app",
                    id=item.id,
                    app_id=item.app_id or "",
                    title=item.title,
                    summary=item.summary,
                    is_favorite=item.is_favorite,
                )
            )
    return ListAllToolsResponse(
        items=items,
        professions=[
            ProfessionItem(
                id=p.id,
                slug=p.slug,
                label=p.label,
                sort_order=p.sort_order,
            )
            for p in result.professions
        ],
        categories=[
            CategoryItem(
                id=c.id,
                slug=c.slug,
                label=c.label,
            )
            for c in result.categories
        ],
    )
