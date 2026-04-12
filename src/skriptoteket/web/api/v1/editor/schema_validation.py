from uuid import UUID

from fastapi import APIRouter, Depends

from skriptoteket.application.scripting.commands import ValidateToolSchemasCommand
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.scripting import ValidateToolSchemasHandlerProtocol
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_contributor_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka

from .models.requests import ValidateToolSchemasRequest
from .models.responses import ValidateToolSchemasResponse

router = APIRouter()


@router.post("/tools/{tool_id}/validate-schemas", response_model=ValidateToolSchemasResponse)
async def validate_schemas(
    tool_id: UUID,
    payload: ValidateToolSchemasRequest,
    handler: FromDishka[ValidateToolSchemasHandlerProtocol],
    user: User = Depends(require_app_contributor_api),
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
