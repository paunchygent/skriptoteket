from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.scripting.commands import ValidateToolSchemasCommand
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.scripting import ValidateToolSchemasHandlerProtocol
from skriptoteket.web.auth.api_dependencies import require_contributor_api, require_csrf_token

from .models import ValidateToolSchemasRequest, ValidateToolSchemasResponse

router = APIRouter()


@router.post("/tools/{tool_id}/validate-schemas", response_model=ValidateToolSchemasResponse)
@inject
async def validate_schemas(
    tool_id: UUID,
    payload: ValidateToolSchemasRequest,
    handler: FromDishka[ValidateToolSchemasHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> ValidateToolSchemasResponse:
    result = await handler.handle(
        actor=user,
        command=ValidateToolSchemasCommand(
            tool_id=tool_id,
            settings_schema=payload.settings_schema,
            input_schema=payload.input_schema,
        ),
    )
    return ValidateToolSchemasResponse(valid=result.valid, issues=result.issues)
