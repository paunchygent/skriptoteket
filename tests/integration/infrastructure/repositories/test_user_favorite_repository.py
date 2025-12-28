from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.domain.favorites.models import FavoriteCatalogItemKind
from skriptoteket.domain.identity.models import AuthProvider, Role
from skriptoteket.infrastructure.db.models.tool import ToolModel
from skriptoteket.infrastructure.db.models.tool_version import ToolVersionModel  # noqa: F401
from skriptoteket.infrastructure.db.models.user import UserModel
from skriptoteket.infrastructure.db.models.user_favorite import (
    UserFavoriteAppModel,
    UserFavoriteToolModel,
)
from skriptoteket.infrastructure.repositories.user_favorite_repository import (
    PostgreSQLFavoritesRepository,
)

pytestmark = pytest.mark.asyncio(loop_scope="module")


@pytest.fixture
def now() -> datetime:
    return datetime.now(timezone.utc)


async def _create_user(
    db_session: AsyncSession,
    *,
    now: datetime,
    role: Role,
    email_prefix: str,
) -> UUID:
    uid = uuid4()
    db_session.add(
        UserModel(
            id=uid,
            email=f"{email_prefix}-{uid.hex[:8]}@example.com",
            password_hash="hash",
            role=role,
            auth_provider=AuthProvider.LOCAL,
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return uid


async def _create_tool(
    db_session: AsyncSession,
    *,
    owner_id: UUID,
    now: datetime,
    slug_prefix: str,
) -> UUID:
    tid = uuid4()
    db_session.add(
        ToolModel(
            id=tid,
            owner_user_id=owner_id,
            slug=f"{slug_prefix}-{tid.hex[:8]}",
            title="Favorite Tool",
            summary="For testing",
            created_at=now,
            updated_at=now,
        )
    )
    await db_session.flush()
    return tid


@pytest.fixture
async def owner_id(db_session: AsyncSession, now: datetime) -> UUID:
    return await _create_user(
        db_session,
        now=now,
        role=Role.ADMIN,
        email_prefix="owner",
    )


@pytest.fixture
async def user_id(db_session: AsyncSession, now: datetime) -> UUID:
    return await _create_user(
        db_session,
        now=now,
        role=Role.USER,
        email_prefix="favorite-user",
    )


@pytest.mark.integration
async def test_tool_favorites_add_idempotent_and_lookup(
    db_session: AsyncSession, owner_id: UUID, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)
    tool_id = await _create_tool(db_session, owner_id=owner_id, now=now, slug_prefix="fav")

    assert await repo.is_favorite_tool(user_id=user_id, tool_id=tool_id) is False

    favorite = await repo.add_tool(user_id=user_id, tool_id=tool_id)
    assert favorite.user_id == user_id
    assert favorite.tool_id == tool_id
    assert favorite.created_at is not None

    await repo.add_tool(user_id=user_id, tool_id=tool_id)

    tool_ids = await repo.list_tool_ids_for_user(user_id=user_id)
    assert tool_ids == [tool_id]

    favorites = await repo.list_favorites_for_tools(
        user_id=user_id,
        tool_ids=[tool_id, uuid4()],
    )
    assert favorites == {tool_id}


@pytest.mark.integration
async def test_tool_favorites_list_order_and_remove(
    db_session: AsyncSession, owner_id: UUID, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)

    older_tool_id = await _create_tool(
        db_session,
        owner_id=owner_id,
        now=now,
        slug_prefix="fav-old",
    )
    newer_tool_id = await _create_tool(
        db_session,
        owner_id=owner_id,
        now=now,
        slug_prefix="fav-new",
    )

    db_session.add(
        UserFavoriteToolModel(
            user_id=user_id,
            tool_id=older_tool_id,
            created_at=now - timedelta(days=1),
        )
    )
    db_session.add(
        UserFavoriteToolModel(
            user_id=user_id,
            tool_id=newer_tool_id,
            created_at=now,
        )
    )
    await db_session.flush()

    tool_ids = await repo.list_tool_ids_for_user(user_id=user_id)
    assert tool_ids == [newer_tool_id, older_tool_id]

    tool_ids_limited = await repo.list_tool_ids_for_user(user_id=user_id, limit=1)
    assert tool_ids_limited == [newer_tool_id]

    await repo.remove_tool(user_id=user_id, tool_id=newer_tool_id)
    assert await repo.is_favorite_tool(user_id=user_id, tool_id=newer_tool_id) is False


@pytest.mark.integration
async def test_tool_favorites_cascade_on_tool_delete(
    db_session: AsyncSession, owner_id: UUID, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)
    tool_id = await _create_tool(db_session, owner_id=owner_id, now=now, slug_prefix="fav-del")

    await repo.add_tool(user_id=user_id, tool_id=tool_id)

    await db_session.execute(delete(ToolModel).where(ToolModel.id == tool_id))
    await db_session.flush()

    assert await repo.is_favorite_tool(user_id=user_id, tool_id=tool_id) is False


@pytest.mark.integration
async def test_app_favorites_add_idempotent_and_lookup(
    db_session: AsyncSession, user_id: UUID
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)
    app_id = "demo.counter"

    assert await repo.is_favorite_app(user_id=user_id, app_id=app_id) is False

    favorite = await repo.add_app(user_id=user_id, app_id=app_id)
    assert favorite.user_id == user_id
    assert favorite.app_id == app_id
    assert favorite.created_at is not None

    await repo.add_app(user_id=user_id, app_id=app_id)

    app_ids = await repo.list_app_ids_for_user(user_id=user_id)
    assert app_ids == [app_id]

    favorites = await repo.list_favorites_for_apps(
        user_id=user_id,
        app_ids=[app_id, "demo.timer"],
    )
    assert favorites == {app_id}


@pytest.mark.integration
async def test_app_favorites_list_order_and_remove(
    db_session: AsyncSession, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)

    older_app_id = "demo.alpha"
    newer_app_id = "demo.beta"

    db_session.add(
        UserFavoriteAppModel(
            user_id=user_id,
            app_id=older_app_id,
            created_at=now - timedelta(days=2),
        )
    )
    db_session.add(
        UserFavoriteAppModel(
            user_id=user_id,
            app_id=newer_app_id,
            created_at=now - timedelta(days=1),
        )
    )
    await db_session.flush()

    app_ids = await repo.list_app_ids_for_user(user_id=user_id)
    assert app_ids == [newer_app_id, older_app_id]

    app_ids_limited = await repo.list_app_ids_for_user(user_id=user_id, limit=1)
    assert app_ids_limited == [newer_app_id]

    await repo.remove_app(user_id=user_id, app_id=newer_app_id)
    assert await repo.is_favorite_app(user_id=user_id, app_id=newer_app_id) is False


@pytest.mark.integration
async def test_list_catalog_refs_for_user_orders_mixed(
    db_session: AsyncSession, owner_id: UUID, user_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)
    tool_id = await _create_tool(db_session, owner_id=owner_id, now=now, slug_prefix="fav-mixed")
    app_id = "demo.mixed"

    db_session.add(
        UserFavoriteToolModel(
            user_id=user_id,
            tool_id=tool_id,
            created_at=now - timedelta(hours=2),
        )
    )
    db_session.add(
        UserFavoriteAppModel(
            user_id=user_id,
            app_id=app_id,
            created_at=now - timedelta(hours=1),
        )
    )
    await db_session.flush()

    refs = await repo.list_catalog_refs_for_user(user_id=user_id)
    assert [(ref.kind, ref.tool_id, ref.app_id) for ref in refs] == [
        (FavoriteCatalogItemKind.CURATED_APP, None, app_id),
        (FavoriteCatalogItemKind.TOOL, tool_id, None),
    ]

    limited = await repo.list_catalog_refs_for_user(user_id=user_id, limit=1)
    assert len(limited) == 1
    assert limited[0].kind is FavoriteCatalogItemKind.CURATED_APP


@pytest.mark.integration
async def test_favorites_cascade_on_user_delete(
    db_session: AsyncSession, owner_id: UUID, now: datetime
) -> None:
    repo = PostgreSQLFavoritesRepository(db_session)

    user_id = await _create_user(
        db_session,
        now=now,
        role=Role.USER,
        email_prefix="cascade-user",
    )
    tool_id = await _create_tool(
        db_session,
        owner_id=owner_id,
        now=now,
        slug_prefix="fav-cascade",
    )

    await repo.add_tool(user_id=user_id, tool_id=tool_id)
    await repo.add_app(user_id=user_id, app_id="demo.gamma")

    await db_session.execute(delete(UserModel).where(UserModel.id == user_id))
    await db_session.flush()

    assert await repo.is_favorite_tool(user_id=user_id, tool_id=tool_id) is False
    assert await repo.is_favorite_app(user_id=user_id, app_id="demo.gamma") is False
