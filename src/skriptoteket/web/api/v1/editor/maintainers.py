from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.catalog.commands import (
    AssignMaintainerCommand,
    RemoveMaintainerCommand,
)
from skriptoteket.application.catalog.queries import ListMaintainersQuery
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.catalog import (
    AssignMaintainerHandlerProtocol,
    ListMaintainersHandlerProtocol,
    RemoveMaintainerHandlerProtocol,
)
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.web.auth.api_dependencies import (
    require_admin_api,
    require_csrf_token,
)

from .models import AssignMaintainerRequest, MaintainerListResponse, MaintainerSummary

router = APIRouter()


def _to_maintainer_summary(user: User) -> MaintainerSummary:
    return MaintainerSummary(
        id=user.id,
        email=user.email,
        role=user.role,
    )


@router.get("/tools/{tool_id}/maintainers", response_model=MaintainerListResponse)
@inject
async def list_tool_maintainers(
    tool_id: UUID,
    handler: FromDishka[ListMaintainersHandlerProtocol],
    user: User = Depends(require_admin_api),
) -> MaintainerListResponse:
    result = await handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return MaintainerListResponse(
        tool_id=result.tool_id,
        owner_user_id=result.owner_user_id,
        maintainers=[_to_maintainer_summary(maintainer) for maintainer in result.maintainers],
    )


@router.post("/tools/{tool_id}/maintainers", response_model=MaintainerListResponse)
@inject
async def assign_tool_maintainer(
    tool_id: UUID,
    payload: AssignMaintainerRequest,
    handler: FromDishka[AssignMaintainerHandlerProtocol],
    list_handler: FromDishka[ListMaintainersHandlerProtocol],
    users: FromDishka[UserRepositoryProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> MaintainerListResponse:
    email = payload.email.strip()
    if not email:
        raise validation_error("E-post krävs.", details={"email": payload.email})

    user_auth = await users.get_auth_by_email(email=email)
    if user_auth is None:
        raise validation_error(
            f"Ingen användare med e-post: {email}",
            details={"email": email},
        )

    await handler.handle(
        actor=user,
        command=AssignMaintainerCommand(
            tool_id=tool_id,
            user_id=user_auth.user.id,
        ),
    )
    result = await list_handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return MaintainerListResponse(
        tool_id=result.tool_id,
        owner_user_id=result.owner_user_id,
        maintainers=[_to_maintainer_summary(maintainer) for maintainer in result.maintainers],
    )


@router.delete("/tools/{tool_id}/maintainers/{user_id}", response_model=MaintainerListResponse)
@inject
async def remove_tool_maintainer(
    tool_id: UUID,
    user_id: UUID,
    handler: FromDishka[RemoveMaintainerHandlerProtocol],
    list_handler: FromDishka[ListMaintainersHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> MaintainerListResponse:
    await handler.handle(
        actor=user,
        command=RemoveMaintainerCommand(
            tool_id=tool_id,
            user_id=user_id,
        ),
    )
    result = await list_handler.handle(
        actor=user,
        query=ListMaintainersQuery(tool_id=tool_id),
    )
    return MaintainerListResponse(
        tool_id=result.tool_id,
        owner_user_id=result.owner_user_id,
        maintainers=[_to_maintainer_summary(maintainer) for maintainer in result.maintainers],
    )
