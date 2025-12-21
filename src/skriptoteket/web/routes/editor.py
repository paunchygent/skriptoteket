from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from pydantic import BaseModel, ConfigDict

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    SaveDraftVersionCommand,
)
from skriptoteket.domain.errors import DomainError
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
)
from skriptoteket.web.auth.dependencies import require_contributor
from skriptoteket.web.error_mapping import error_to_status
from skriptoteket.web.toasts import set_toast_cookie
from skriptoteket.web.ui_text import ui_error_message

router = APIRouter(prefix="/api/editor")


class CreateDraftVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = "run_tool"
    source_code: str
    change_summary: str | None = None
    derived_from_version_id: UUID | None = None


class SaveDraftVersionRequest(BaseModel):
    model_config = ConfigDict(frozen=True)

    entrypoint: str = "run_tool"
    source_code: str
    change_summary: str | None = None
    expected_parent_version_id: UUID


class SaveResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    version_id: UUID
    redirect_url: str


@router.post("/tools/{tool_id}/draft", response_model=SaveResult)
@inject
async def create_draft_version(
    tool_id: UUID,
    payload: CreateDraftVersionRequest,
    handler: FromDishka[CreateDraftVersionHandlerProtocol],
    user: User = Depends(require_contributor),
) -> Response:
    try:
        result = await handler.handle(
            actor=user,
            command=CreateDraftVersionCommand(
                tool_id=tool_id,
                derived_from_version_id=payload.derived_from_version_id,
                entrypoint=payload.entrypoint,
                source_code=payload.source_code,
                change_summary=payload.change_summary,
            ),
        )
    except DomainError as exc:
        return JSONResponse(
            status_code=error_to_status(exc.code),
            content={
                "error": {
                    "code": exc.code.value,
                    "message": ui_error_message(exc),
                    "details": exc.details,
                }
            },
        )

    redirect_url = f"/admin/tool-versions/{result.version.id}"
    response = JSONResponse(
        status_code=200,
        content={
            "version_id": str(result.version.id),
            "redirect_url": redirect_url,
        },
    )
    set_toast_cookie(response=response, message="Utkast skapat.", toast_type="success")
    return response


@router.post("/tool-versions/{version_id}/save", response_model=SaveResult)
@inject
async def save_draft_version(
    version_id: UUID,
    payload: SaveDraftVersionRequest,
    handler: FromDishka[SaveDraftVersionHandlerProtocol],
    user: User = Depends(require_contributor),
) -> Response:
    try:
        result = await handler.handle(
            actor=user,
            command=SaveDraftVersionCommand(
                version_id=version_id,
                expected_parent_version_id=payload.expected_parent_version_id,
                entrypoint=payload.entrypoint,
                source_code=payload.source_code,
                change_summary=payload.change_summary,
            ),
        )
    except DomainError as exc:
        return JSONResponse(
            status_code=error_to_status(exc.code),
            content={
                "error": {
                    "code": exc.code.value,
                    "message": ui_error_message(exc),
                    "details": exc.details,
                }
            },
        )

    redirect_url = f"/admin/tool-versions/{result.version.id}"
    response = JSONResponse(
        status_code=200,
        content={
            "version_id": str(result.version.id),
            "redirect_url": redirect_url,
        },
    )
    set_toast_cookie(response=response, message="Sparat.", toast_type="success")
    return response
