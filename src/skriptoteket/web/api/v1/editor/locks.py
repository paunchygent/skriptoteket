from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.scripting.draft_locks import (
    AcquireDraftLockCommand,
    ReleaseDraftLockCommand,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.draft_locks import (
    AcquireDraftLockHandlerProtocol,
    ReleaseDraftLockHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_contributor_api,
    require_csrf_token,
)

from .models import DraftLockReleaseResponse, DraftLockRequest, DraftLockResponse

router = APIRouter()


@router.post("/tools/{tool_id}/draft-lock", response_model=DraftLockResponse)
@inject
async def acquire_draft_lock(
    tool_id: UUID,
    payload: DraftLockRequest,
    handler: FromDishka[AcquireDraftLockHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> DraftLockResponse:
    result = await handler.handle(
        actor=user,
        command=AcquireDraftLockCommand(
            tool_id=tool_id,
            draft_head_id=payload.draft_head_id,
            force=payload.force,
        ),
    )
    return DraftLockResponse(
        tool_id=result.tool_id,
        draft_head_id=result.draft_head_id,
        locked_by_user_id=result.locked_by_user_id,
        expires_at=result.expires_at,
        is_owner=result.is_owner,
    )


@router.delete("/tools/{tool_id}/draft-lock", response_model=DraftLockReleaseResponse)
@inject
async def release_draft_lock(
    tool_id: UUID,
    handler: FromDishka[ReleaseDraftLockHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> DraftLockReleaseResponse:
    result = await handler.handle(
        actor=user,
        command=ReleaseDraftLockCommand(tool_id=tool_id),
    )
    return DraftLockReleaseResponse(tool_id=result.tool_id)
