from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.scripting.commands import (
    CreateDraftVersionCommand,
    SaveDraftVersionCommand,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.scripting import (
    CreateDraftVersionHandlerProtocol,
    SaveDraftVersionHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_contributor_api,
    require_csrf_token,
)

from .models import CreateDraftVersionRequest, SaveDraftVersionRequest, SaveResult

router = APIRouter()


@router.post("/tools/{tool_id}/draft", response_model=SaveResult)
@inject
async def create_draft_version(
    tool_id: UUID,
    payload: CreateDraftVersionRequest,
    handler: FromDishka[CreateDraftVersionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SaveResult:
    command_payload: dict[str, object] = {
        "tool_id": tool_id,
        "derived_from_version_id": payload.derived_from_version_id,
        "entrypoint": payload.entrypoint,
        "source_code": payload.source_code,
        "change_summary": payload.change_summary,
    }
    if "settings_schema" in payload.model_fields_set:
        command_payload["settings_schema"] = payload.settings_schema
    if "input_schema" in payload.model_fields_set:
        command_payload["input_schema"] = payload.input_schema
    if "usage_instructions" in payload.model_fields_set:
        command_payload["usage_instructions"] = payload.usage_instructions
    result = await handler.handle(
        actor=user,
        command=CreateDraftVersionCommand.model_validate(command_payload),
    )
    return SaveResult(
        version_id=result.version.id,
        redirect_url=f"/admin/tool-versions/{result.version.id}",
    )


@router.post("/tool-versions/{version_id}/save", response_model=SaveResult)
@inject
async def save_draft_version(
    version_id: UUID,
    payload: SaveDraftVersionRequest,
    handler: FromDishka[SaveDraftVersionHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SaveResult:
    command_payload: dict[str, object] = {
        "version_id": version_id,
        "expected_parent_version_id": payload.expected_parent_version_id,
        "entrypoint": payload.entrypoint,
        "source_code": payload.source_code,
        "change_summary": payload.change_summary,
    }
    if "settings_schema" in payload.model_fields_set:
        command_payload["settings_schema"] = payload.settings_schema
    if "input_schema" in payload.model_fields_set:
        command_payload["input_schema"] = payload.input_schema
    if "usage_instructions" in payload.model_fields_set:
        command_payload["usage_instructions"] = payload.usage_instructions
    result = await handler.handle(
        actor=user,
        command=SaveDraftVersionCommand.model_validate(command_payload),
    )
    return SaveResult(
        version_id=result.version.id,
        redirect_url=f"/admin/tool-versions/{result.version.id}",
    )
