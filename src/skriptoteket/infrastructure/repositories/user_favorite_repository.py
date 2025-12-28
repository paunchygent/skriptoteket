from __future__ import annotations

from uuid import UUID

from sqlalchemy import String, delete, literal, select, union_all
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.errors import not_found
from skriptoteket.domain.favorites.models import (
    FavoriteCatalogItemKind,
    FavoriteCatalogRef,
    UserFavoriteCuratedApp,
    UserFavoriteTool,
)
from skriptoteket.infrastructure.db.models.user_favorite import (
    UserFavoriteAppModel,
    UserFavoriteToolModel,
)
from skriptoteket.protocols.favorites import FavoritesRepositoryProtocol


class PostgreSQLFavoritesRepository(FavoritesRepositoryProtocol):
    """PostgreSQL repository for user favorites.

    Uses a request-scoped `AsyncSession`; commit/rollback is owned by the Unit of Work.
    """

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def add_tool(self, *, user_id: UUID, tool_id: UUID) -> UserFavoriteTool:
        stmt = (
            insert(UserFavoriteToolModel)
            .values(user_id=user_id, tool_id=tool_id)
            .on_conflict_do_nothing(
                index_elements=[
                    UserFavoriteToolModel.user_id,
                    UserFavoriteToolModel.tool_id,
                ]
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self._get_tool_favorite(user_id=user_id, tool_id=tool_id)

    async def remove_tool(self, *, user_id: UUID, tool_id: UUID) -> None:
        await self._session.execute(
            delete(UserFavoriteToolModel).where(
                UserFavoriteToolModel.user_id == user_id,
                UserFavoriteToolModel.tool_id == tool_id,
            )
        )
        await self._session.flush()

    async def is_favorite_tool(self, *, user_id: UUID, tool_id: UUID) -> bool:
        stmt = (
            select(UserFavoriteToolModel)
            .where(
                UserFavoriteToolModel.user_id == user_id,
                UserFavoriteToolModel.tool_id == tool_id,
            )
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_tool_ids_for_user(
        self, *, user_id: UUID, limit: int | None = None
    ) -> list[UUID]:
        stmt = (
            select(UserFavoriteToolModel.tool_id)
            .where(UserFavoriteToolModel.user_id == user_id)
            .order_by(
                UserFavoriteToolModel.created_at.desc(),
                UserFavoriteToolModel.tool_id.asc(),
            )
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_favorites_for_tools(self, *, user_id: UUID, tool_ids: list[UUID]) -> set[UUID]:
        if not tool_ids:
            return set()
        stmt = select(UserFavoriteToolModel.tool_id).where(
            UserFavoriteToolModel.user_id == user_id,
            UserFavoriteToolModel.tool_id.in_(tool_ids),
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def list_catalog_refs_for_user(
        self, *, user_id: UUID, limit: int | None = None
    ) -> list[FavoriteCatalogRef]:
        tool_stmt = (
            select(
                literal(FavoriteCatalogItemKind.TOOL.value).label("kind"),
                UserFavoriteToolModel.tool_id.label("tool_id"),
                literal(None, type_=String(128)).label("app_id"),
                UserFavoriteToolModel.created_at.label("created_at"),
            )
            .where(UserFavoriteToolModel.user_id == user_id)
            .correlate(None)
        )
        app_stmt = (
            select(
                literal(FavoriteCatalogItemKind.CURATED_APP.value).label("kind"),
                literal(None, type_=PGUUID(as_uuid=True)).label("tool_id"),
                UserFavoriteAppModel.app_id.label("app_id"),
                UserFavoriteAppModel.created_at.label("created_at"),
            )
            .where(UserFavoriteAppModel.user_id == user_id)
            .correlate(None)
        )
        union_stmt = union_all(tool_stmt, app_stmt).subquery()

        stmt = select(
            union_stmt.c.kind,
            union_stmt.c.tool_id,
            union_stmt.c.app_id,
            union_stmt.c.created_at,
        ).order_by(
            union_stmt.c.created_at.desc(),
            union_stmt.c.kind.asc(),
            union_stmt.c.tool_id.asc().nulls_last(),
            union_stmt.c.app_id.asc().nulls_last(),
        )
        if limit is not None:
            stmt = stmt.limit(limit)

        result = await self._session.execute(stmt)
        rows = result.mappings().all()
        return [FavoriteCatalogRef.model_validate(row) for row in rows]

    async def add_app(self, *, user_id: UUID, app_id: str) -> UserFavoriteCuratedApp:
        stmt = (
            insert(UserFavoriteAppModel)
            .values(user_id=user_id, app_id=app_id)
            .on_conflict_do_nothing(
                index_elements=[
                    UserFavoriteAppModel.user_id,
                    UserFavoriteAppModel.app_id,
                ]
            )
        )
        await self._session.execute(stmt)
        await self._session.flush()
        return await self._get_app_favorite(user_id=user_id, app_id=app_id)

    async def remove_app(self, *, user_id: UUID, app_id: str) -> None:
        await self._session.execute(
            delete(UserFavoriteAppModel).where(
                UserFavoriteAppModel.user_id == user_id,
                UserFavoriteAppModel.app_id == app_id,
            )
        )
        await self._session.flush()

    async def is_favorite_app(self, *, user_id: UUID, app_id: str) -> bool:
        stmt = (
            select(UserFavoriteAppModel)
            .where(UserFavoriteAppModel.user_id == user_id, UserFavoriteAppModel.app_id == app_id)
            .limit(1)
        )
        result = await self._session.execute(stmt)
        return result.scalar_one_or_none() is not None

    async def list_app_ids_for_user(self, *, user_id: UUID, limit: int | None = None) -> list[str]:
        stmt = (
            select(UserFavoriteAppModel.app_id)
            .where(UserFavoriteAppModel.user_id == user_id)
            .order_by(
                UserFavoriteAppModel.created_at.desc(),
                UserFavoriteAppModel.app_id.asc(),
            )
        )
        if limit is not None:
            stmt = stmt.limit(limit)
        result = await self._session.execute(stmt)
        return list(result.scalars().all())

    async def list_favorites_for_apps(self, *, user_id: UUID, app_ids: list[str]) -> set[str]:
        if not app_ids:
            return set()
        stmt = select(UserFavoriteAppModel.app_id).where(
            UserFavoriteAppModel.user_id == user_id,
            UserFavoriteAppModel.app_id.in_(app_ids),
        )
        result = await self._session.execute(stmt)
        return set(result.scalars().all())

    async def _get_tool_favorite(self, *, user_id: UUID, tool_id: UUID) -> UserFavoriteTool:
        stmt = select(UserFavoriteToolModel).where(
            UserFavoriteToolModel.user_id == user_id,
            UserFavoriteToolModel.tool_id == tool_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise not_found("UserFavoriteTool", f"{user_id}:{tool_id}")
        return UserFavoriteTool.model_validate(model)

    async def _get_app_favorite(self, *, user_id: UUID, app_id: str) -> UserFavoriteCuratedApp:
        stmt = select(UserFavoriteAppModel).where(
            UserFavoriteAppModel.user_id == user_id,
            UserFavoriteAppModel.app_id == app_id,
        )
        result = await self._session.execute(stmt)
        model = result.scalar_one_or_none()
        if model is None:
            raise not_found("UserFavoriteCuratedApp", f"{user_id}:{app_id}")
        return UserFavoriteCuratedApp.model_validate(model)
