"""Admin users API endpoints (superuser-only)."""

from __future__ import annotations

from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.identity.admin_users import GetUserQuery, ListUsersQuery
from skriptoteket.application.identity.login_events import ListLoginEventsQuery
from skriptoteket.domain.identity.login_events import LoginEvent
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.identity import (
    GetUserHandlerProtocol,
    ListUsersHandlerProtocol,
)
from skriptoteket.protocols.login_events import ListLoginEventsHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_superuser_api

router = APIRouter(prefix="/api/v1", tags=["admin-users"])


class ListAdminUsersResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    users: list[User]
    total: int


class AdminUserResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User


class AdminUserLoginEventsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    user: User
    events: list[LoginEvent]


@router.get("/admin/users", response_model=ListAdminUsersResponse)
@inject
async def list_admin_users(
    handler: FromDishka[ListUsersHandlerProtocol],
    user: User = Depends(require_superuser_api),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> ListAdminUsersResponse:
    result = await handler.handle(
        actor=user,
        query=ListUsersQuery(limit=limit, offset=offset),
    )
    return ListAdminUsersResponse(users=result.users, total=result.total)


@router.get("/admin/users/{user_id}", response_model=AdminUserResponse)
@inject
async def get_admin_user(
    user_id: UUID,
    handler: FromDishka[GetUserHandlerProtocol],
    user: User = Depends(require_superuser_api),
) -> AdminUserResponse:
    result = await handler.handle(actor=user, query=GetUserQuery(user_id=user_id))
    return AdminUserResponse(user=result.user)


@router.get("/admin/users/{user_id}/login-events", response_model=AdminUserLoginEventsResponse)
@inject
async def get_admin_user_login_events(
    user_id: UUID,
    handler: FromDishka[ListLoginEventsHandlerProtocol],
    user_handler: FromDishka[GetUserHandlerProtocol],
    user: User = Depends(require_superuser_api),
    limit: int = Query(50, ge=1, le=200),
) -> AdminUserLoginEventsResponse:
    user_result = await user_handler.handle(actor=user, query=GetUserQuery(user_id=user_id))
    events_result = await handler.handle(
        actor=user,
        query=ListLoginEventsQuery(user_id=user_id, limit=limit),
    )
    return AdminUserLoginEventsResponse(user=user_result.user, events=events_result.events)
