from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.scripting.commands import (
    PublishVersionCommand,
    RequestChangesCommand,
    RollbackVersionCommand,
    SubmitForReviewCommand,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.scripting import (
    PublishVersionHandlerProtocol,
    RequestChangesHandlerProtocol,
    RollbackVersionHandlerProtocol,
    SubmitForReviewHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_admin_api,
    require_contributor_api,
    require_csrf_token,
    require_superuser_api,
)

from .models import (
    PublishVersionRequest,
    RequestChangesRequest,
    SubmitReviewRequest,
    WorkflowActionResponse,
)

router = APIRouter()


@router.post("/tool-versions/{version_id}/submit-review", response_model=WorkflowActionResponse)
@inject
async def submit_review(
    version_id: UUID,
    payload: SubmitReviewRequest,
    handler: FromDishka[SubmitForReviewHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=SubmitForReviewCommand(
            version_id=version_id,
            review_note=payload.review_note,
        ),
    )
    return WorkflowActionResponse(
        version_id=result.version.id,
        redirect_url=f"/admin/tool-versions/{result.version.id}",
    )


@router.post("/tool-versions/{version_id}/publish", response_model=WorkflowActionResponse)
@inject
async def publish_version(
    version_id: UUID,
    payload: PublishVersionRequest,
    handler: FromDishka[PublishVersionHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=PublishVersionCommand(
            version_id=version_id,
            change_summary=payload.change_summary,
        ),
    )
    return WorkflowActionResponse(
        version_id=result.new_active_version.id,
        redirect_url=f"/admin/tool-versions/{result.new_active_version.id}",
    )


@router.post("/tool-versions/{version_id}/request-changes", response_model=WorkflowActionResponse)
@inject
async def request_changes(
    version_id: UUID,
    payload: RequestChangesRequest,
    handler: FromDishka[RequestChangesHandlerProtocol],
    user: User = Depends(require_admin_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=RequestChangesCommand(
            version_id=version_id,
            message=payload.message,
        ),
    )
    return WorkflowActionResponse(
        version_id=result.new_draft_version.id,
        redirect_url=f"/admin/tool-versions/{result.new_draft_version.id}",
    )


@router.post("/tool-versions/{version_id}/rollback", response_model=WorkflowActionResponse)
@inject
async def rollback_version(
    version_id: UUID,
    handler: FromDishka[RollbackVersionHandlerProtocol],
    user: User = Depends(require_superuser_api),
    _: None = Depends(require_csrf_token),
) -> WorkflowActionResponse:
    result = await handler.handle(
        actor=user,
        command=RollbackVersionCommand(version_id=version_id),
    )
    new_active = result.new_active_version
    return WorkflowActionResponse(
        version_id=new_active.id,
        redirect_url=f"/admin/tool-versions/{new_active.id}",
    )
