"""Catalog API endpoints for SPA browse views (ST-11-06)."""

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.catalog.queries import (
    ListAllCategoriesQuery,
    ListCategoriesForProfessionQuery,
    ListProfessionsQuery,
    ListToolsByTagsQuery,
)
from skriptoteket.domain.identity.models import Role, User
from skriptoteket.protocols.catalog import (
    ListAllCategoriesHandlerProtocol,
    ListCategoriesForProfessionHandlerProtocol,
    ListProfessionsHandlerProtocol,
    ListToolsByTagsHandlerProtocol,
)
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.auth.api_dependencies import require_user_api

router = APIRouter(prefix="/api/v1/catalog", tags=["catalog"])


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
