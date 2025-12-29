from uuid import UUID

from dishka.integrations.fastapi import FromDishka, inject
from fastapi import APIRouter, Depends

from skriptoteket.application.scripting.tool_settings import (
    ResolveSandboxSettingsQuery,
    SaveSandboxSettingsCommand,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.tool_settings import (
    ResolveSandboxSettingsHandlerProtocol,
    SaveSandboxSettingsHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import (
    require_contributor_api,
    require_csrf_token,
)

from .models import (
    SandboxSettingsResolveRequest,
    SandboxSettingsResponse,
    SandboxSettingsSaveRequest,
)

router = APIRouter()


@router.post(
    "/tool-versions/{version_id}/sandbox-settings/resolve",
    response_model=SandboxSettingsResponse,
)
@inject
async def resolve_sandbox_settings(
    version_id: UUID,
    payload: SandboxSettingsResolveRequest,
    handler: FromDishka[ResolveSandboxSettingsHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SandboxSettingsResponse:
    result = await handler.handle(
        actor=user,
        query=ResolveSandboxSettingsQuery(
            version_id=version_id,
            settings_schema=payload.settings_schema,
        ),
    )
    settings_state = result.settings
    return SandboxSettingsResponse(
        tool_id=settings_state.tool_id,
        schema_version=settings_state.schema_version,
        settings_schema=settings_state.settings_schema,
        values=settings_state.values,
        state_rev=settings_state.state_rev,
    )


@router.put(
    "/tool-versions/{version_id}/sandbox-settings",
    response_model=SandboxSettingsResponse,
)
@inject
async def save_sandbox_settings(
    version_id: UUID,
    payload: SandboxSettingsSaveRequest,
    handler: FromDishka[SaveSandboxSettingsHandlerProtocol],
    user: User = Depends(require_contributor_api),
    _: None = Depends(require_csrf_token),
) -> SandboxSettingsResponse:
    result = await handler.handle(
        actor=user,
        command=SaveSandboxSettingsCommand(
            version_id=version_id,
            settings_schema=payload.settings_schema,
            expected_state_rev=payload.expected_state_rev,
            values=payload.values,
        ),
    )
    settings_state = result.settings
    return SandboxSettingsResponse(
        tool_id=settings_state.tool_id,
        schema_version=settings_state.schema_version,
        settings_schema=settings_state.settings_schema,
        values=settings_state.values,
        state_rev=settings_state.state_rev,
    )
