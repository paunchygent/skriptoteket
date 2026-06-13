"""Conversion Hub transcript save API routes.

Domain purpose:
  Expose durable transcript JSON save and readback routes for the authenticated
  Conversion Hub app without introducing downstream formatter/export choices.

Relationships:
  - Uses the Conversion Hub app-access policy from `apps_conversion_hub_access`.
  - Delegates owner-scope and validation to transcript save handlers.
  - Registered by `web.router` before the SPA fallback.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, Request, Response

from skriptoteket.application.curated_apps.conversion_hub import (
    RegisterTranscriptConversionHubJobRequest,
    RegisterTranscriptConversionHubJobResult,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_artifact_actions import (
    SaveConversionHubTranscriptFormatterArtifactResult,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_replay import (
    ConversionHubTranscriptFormatterArtifactKey,
    ConversionHubTranscriptFormatterReplayCompleteRequest,
    ConversionHubTranscriptFormatterReplayPrepareRequest,
    ConversionHubTranscriptFormatterReplayPrepareResponse,
    ConversionHubTranscriptFormatterReplayResponse,
)
from skriptoteket.application.curated_apps.conversion_hub_transcript_saves import (
    ConversionHubSavedTranscriptResponse,
    ConversionHubTranscriptSpeakerOverlaysResponse,
    SaveConversionHubTranscriptRequest,
    UpdateConversionHubTranscriptSpeakerOverlaysRequest,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_artifact_actions as transcript_artifact_action_handlers,
)
from skriptoteket.application.curated_apps.handlers import (
    conversion_hub_transcript_formatter_replay as transcript_replay_handlers,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
    RegisterTranscriptConversionHubJobHandler,
)
from skriptoteket.application.curated_apps.handlers.conversion_hub_transcript_saves import (
    GetConversionHubTranscriptHandler,
    ListConversionHubTranscriptSpeakerOverlaysHandler,
    SaveConversionHubTranscriptHandler,
    UpdateConversionHubTranscriptSpeakerOverlaysHandler,
)
from skriptoteket.application.identity.huleedu_app_projection import HuleEduAppUserProjection
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import (
    require_app_user_api,
    require_app_user_projection_api,
)
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.request_metadata import get_correlation_id

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}/transcripts", tags=["apps"])


def _require_app_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    require_conversion_hub_access(registry=registry, user=user)


@router.post("/jobs/{job_id}", response_model=ConversionHubSavedTranscriptResponse)
async def save_conversion_hub_transcript(
    job_id: UUID,
    request: SaveConversionHubTranscriptRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveConversionHubTranscriptHandler],
    user: User = Depends(require_app_user_api),
) -> ConversionHubSavedTranscriptResponse:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, conversion_hub_job_id=job_id, request=request)


@router.post("/jobs", response_model=RegisterTranscriptConversionHubJobResult)
async def register_transcript_job(
    register_request: RegisterTranscriptConversionHubJobRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RegisterTranscriptConversionHubJobHandler],
    user: User = Depends(require_app_user_api),
) -> RegisterTranscriptConversionHubJobResult:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, request=register_request)


@router.get("/{transcript_id}", response_model=ConversionHubSavedTranscriptResponse)
async def get_conversion_hub_transcript(
    transcript_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetConversionHubTranscriptHandler],
    user: User = Depends(require_app_user_api),
) -> ConversionHubSavedTranscriptResponse:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, transcript_id=transcript_id)


@router.get(
    "/{transcript_id}/speaker-overlays",
    response_model=ConversionHubTranscriptSpeakerOverlaysResponse,
)
async def list_conversion_hub_transcript_speaker_overlays(
    transcript_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ListConversionHubTranscriptSpeakerOverlaysHandler],
    user: User = Depends(require_app_user_api),
) -> ConversionHubTranscriptSpeakerOverlaysResponse:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, transcript_id=transcript_id)


@router.put(
    "/{transcript_id}/speaker-overlays",
    response_model=ConversionHubTranscriptSpeakerOverlaysResponse,
)
async def update_conversion_hub_transcript_speaker_overlays(
    transcript_id: UUID,
    request: UpdateConversionHubTranscriptSpeakerOverlaysRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[UpdateConversionHubTranscriptSpeakerOverlaysHandler],
    user: User = Depends(require_app_user_api),
) -> ConversionHubTranscriptSpeakerOverlaysResponse:
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, transcript_id=transcript_id, request=request)


@router.post(
    "/{transcript_id}/formatter-replay/prepare",
    response_model=ConversionHubTranscriptFormatterReplayPrepareResponse,
)
async def prepare_conversion_hub_transcript_formatter_replay(
    transcript_id: UUID,
    replay_request: ConversionHubTranscriptFormatterReplayPrepareRequest,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[
        transcript_replay_handlers.PrepareConversionHubTranscriptFormatterReplayHandler
    ],
    user: User = Depends(require_app_user_api),
) -> ConversionHubTranscriptFormatterReplayPrepareResponse:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    correlation_id = str(correlation_id_uuid) if correlation_id_uuid is not None else None
    return await handler.handle(
        actor=user,
        transcript_id=transcript_id,
        request=replay_request,
        correlation_id=correlation_id,
    )


@router.post(
    "/{transcript_id}/formatter-replay/complete",
    response_model=ConversionHubTranscriptFormatterReplayResponse,
)
async def complete_conversion_hub_transcript_formatter_replay(
    transcript_id: UUID,
    replay_request: ConversionHubTranscriptFormatterReplayCompleteRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[
        transcript_replay_handlers.CompleteConversionHubTranscriptFormatterReplayHandler
    ],
    projection: HuleEduAppUserProjection = Depends(require_app_user_projection_api),
) -> ConversionHubTranscriptFormatterReplayResponse:
    user = projection.user
    _require_app_access(registry=registry, user=user)
    return await handler.handle(
        actor=user,
        authenticated_huleedu_subject=projection.realm_subject_id,
        transcript_id=transcript_id,
        request=replay_request,
    )


@router.get("/{transcript_id}/formatter-artifacts/{artifact_key}/download")
async def download_conversion_hub_transcript_formatter_artifact(
    transcript_id: UUID,
    artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[
        transcript_artifact_action_handlers.DownloadConversionHubTranscriptFormatterArtifactHandler
    ],
    user: User = Depends(require_app_user_api),
) -> Response:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    result = await handler.handle(
        actor=user,
        transcript_id=transcript_id,
        artifact_key=artifact_key,
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
    return Response(
        content=result.content,
        media_type=result.content_type,
        headers={
            "Cache-Control": "no-store",
            "Content-Disposition": f'attachment; filename="{result.filename}"',
        },
    )


@router.post(
    "/{transcript_id}/formatter-artifacts/{artifact_key}/save",
    response_model=SaveConversionHubTranscriptFormatterArtifactResult,
)
async def save_conversion_hub_transcript_formatter_artifact(
    transcript_id: UUID,
    artifact_key: ConversionHubTranscriptFormatterArtifactKey,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[
        transcript_artifact_action_handlers.SaveConversionHubTranscriptFormatterArtifactHandler
    ],
    user: User = Depends(require_app_user_api),
) -> SaveConversionHubTranscriptFormatterArtifactResult:
    _require_app_access(registry=registry, user=user)
    correlation_id_uuid = get_correlation_id(request)
    return await handler.handle(
        actor=user,
        transcript_id=transcript_id,
        artifact_key=artifact_key,
        correlation_id=str(correlation_id_uuid) if correlation_id_uuid is not None else None,
    )
