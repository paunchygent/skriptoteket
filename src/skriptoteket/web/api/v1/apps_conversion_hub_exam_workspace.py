"""Exam workspace API routes (ST-SKRIPT-39-04 walking skeleton).

Purpose:
  Expose DOCX import, listing, reopen, save, history, copy and exports for the native editable
  exam workspace under the Conversion Hub curated app.

Relationships:
  - Shares Conversion Hub app access with `apps_conversion_hub`.
  - Delegates behavior to the exam workspace application handlers; the
    native document persists in one Mina filer container with a separate editor history.
"""

from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Request, Response, UploadFile
from starlette.datastructures import UploadFile as StarletteUploadFile

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamCourseCatalogResponse,
    ExamWorkspaceConversionStatus,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentResponse,
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportTarget,
    ExamWorkspaceItemRetryResponse,
    RetryExamWorkspaceItemRequest,
    SaveExamWorkspaceDocumentRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_history import (
    ExamWorkspaceHistoryDocumentResponse,
    ExamWorkspaceHistoryResponse,
    ExamWorkspaceUndoStepResponse,
    SaveAsExamWorkspaceDocumentRequest,
    StoreExamWorkspaceUndoStepRequest,
)
from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
    ExamWorkspaceMisspellingsResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ContentSuggestionsResponse,
    ExamCourseContentResponse,
    GetExamContentSuggestionsHandler,
    RequestExamContentSuggestionsHandler,
    course_content,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    asset_mismatch_error,
)
from skriptoteket.config import Settings
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    parse_native_exam_document,
)
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultFile
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    ExportExamWorkspaceDocumentHandlerProtocol,
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    GetExamCourseCatalogHandlerProtocol,
    GetExamWorkspaceConversionStatusHandlerProtocol,
    GetExamWorkspaceDocumentHandlerProtocol,
    ImportExamWorkspaceDigiExamDocumentHandlerProtocol,
    ImportExamWorkspaceDocumentHandlerProtocol,
    ListExamWorkspaceDocumentsHandlerProtocol,
    RetryExamWorkspaceItemHandlerProtocol,
    SaveExamWorkspaceDocumentHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_guest_drafts import (
    ImportGuestExamDraftHandlerProtocol,
)
from skriptoteket.protocols.exam_workspace_history import StoreExamWorkspaceUndoStepHandlerProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_ai_api, require_app_user_api
from skriptoteket.web.content_disposition import attachment_content_disposition
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(prefix=f"/api/v1/apps/{APP_ID}", tags=["apps"])


@router.get("/exam-workspace/courses/{key:path}/content", response_model=ExamCourseContentResponse)
def get_exam_course_content(
    key: str,
    registry: FromDishka[CuratedAppRegistryProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamCourseContentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return course_content(key)


@router.post(
    "/exam-workspace/documents/{lineage_id}/content-suggestions",
    response_model=ContentSuggestionsResponse,
    status_code=202,
)
async def request_exam_content_suggestions(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RequestExamContentSuggestionsHandler],
    user: User = Depends(require_app_ai_api),
) -> ContentSuggestionsResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id)


@router.get(
    "/exam-workspace/documents/{lineage_id}/content-suggestions/{job_id}",
    response_model=ContentSuggestionsResponse,
)
async def get_exam_content_suggestions(
    lineage_id: UUID,
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamContentSuggestionsHandler],
    user: User = Depends(require_app_user_api),
) -> ContentSuggestionsResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, job_id=job_id)


@router.post(
    "/exam-workspace/answer-misspellings",
    response_model=ExamWorkspaceMisspellingsResponse,
)
def generate_exam_workspace_misspellings(
    request: ExamWorkspaceMisspellingsRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GenerateExamWorkspaceMisspellingsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceMisspellingsResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return handler.handle(request=request)


@router.get(
    "/exam-workspace/documents",
    response_model=ExamWorkspaceDocumentListResponse,
)
async def list_exam_workspace_documents(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ListExamWorkspaceDocumentsHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentListResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user)


@router.post(
    "/exam-workspace/documents",
    response_model=ExamWorkspaceConversionStatus,
    status_code=202,
)
async def import_exam_workspace_document(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ImportExamWorkspaceDocumentHandlerProtocol],
    file: UploadFile = File(...),
    course_key: str | None = Form(None, max_length=64),
    user: User = Depends(require_app_ai_api),
) -> ExamWorkspaceConversionStatus:
    require_conversion_hub_access(registry=registry, user=user)
    content = await file.read()
    return await handler.handle(
        actor=user,
        filename=file.filename or "prov.docx",
        content=content,
        course_key=course_key or None,
    )


@router.post(
    "/exam-workspace/import-digiexam",
    response_model=ExamWorkspaceConversionStatus,
    status_code=202,
)
async def import_exam_workspace_digiexam_document(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ImportExamWorkspaceDigiExamDocumentHandlerProtocol],
    file: UploadFile = File(...),
    course_key: str | None = Form(None, max_length=64),
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceConversionStatus:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(
        actor=user,
        filename=file.filename or "prov.dxe",
        content=await file.read(),
        course_key=course_key or None,
    )


@router.get(
    "/exam-workspace/courses",
    response_model=ExamCourseCatalogResponse,
)
async def get_exam_course_catalog(
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamCourseCatalogHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamCourseCatalogResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user)


@router.get(
    "/exam-workspace/conversion-jobs/{job_id}",
    response_model=ExamWorkspaceConversionStatus,
)
async def get_exam_workspace_conversion_status(
    job_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceConversionStatusHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceConversionStatus:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, job_id=job_id)


@router.get(
    "/exam-workspace/documents/{lineage_id}",
    response_model=ExamWorkspaceDocumentResponse,
)
async def get_exam_workspace_document(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id)


@router.get("/exam-workspace/documents/{lineage_id}/exports/{target}")
async def export_exam_workspace_document(
    lineage_id: UUID,
    target: ExamWorkspaceExportTarget,
    expected_revision: int,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> Response:
    require_conversion_hub_access(registry=registry, user=user)
    result = await handler.handle(
        actor=user, lineage_id=lineage_id, target=target, expected_revision=expected_revision
    )
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": attachment_content_disposition(filename=result.filename)},
    )


@router.get(
    "/exam-workspace/documents/{lineage_id}/export-checklist",
    response_model=ExamWorkspaceExportChecklistResponse,
)
async def export_exam_workspace_document_checklist(
    lineage_id: UUID,
    expected_revision: int,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceExportChecklistResponse:
    """List what an Exam.net import of this document's QTI package loses (Q15)."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.checklist(
        actor=user, lineage_id=lineage_id, expected_revision=expected_revision
    )


@router.put(
    "/exam-workspace/documents/{lineage_id}",
    response_model=ExamWorkspaceDocumentResponse,
)
async def save_exam_workspace_document(
    lineage_id: UUID,
    request: SaveExamWorkspaceDocumentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)


@router.post(
    "/exam-workspace/documents/{lineage_id}/autosaves", response_model=ExamWorkspaceUndoStepResponse
)
async def autosave_exam_workspace_document(
    lineage_id: UUID,
    request: StoreExamWorkspaceUndoStepRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[StoreExamWorkspaceUndoStepHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceUndoStepResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)


@router.get(
    "/exam-workspace/documents/{lineage_id}/history", response_model=ExamWorkspaceHistoryResponse
)
async def get_exam_workspace_history(
    lineage_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceHistoryResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.history(actor=user, lineage_id=lineage_id)


@router.get(
    "/exam-workspace/documents/{lineage_id}/history/{step_id}",
    response_model=ExamWorkspaceHistoryDocumentResponse,
)
async def get_exam_workspace_history_step(
    lineage_id: UUID,
    step_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceHistoryDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.history_step(actor=user, lineage_id=lineage_id, step_id=step_id)


@router.post(
    "/exam-workspace/documents/{lineage_id}/copy", response_model=ExamWorkspaceDocumentResponse
)
async def copy_exam_workspace_document(
    lineage_id: UUID,
    request: SaveAsExamWorkspaceDocumentRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.save_as(actor=user, lineage_id=lineage_id, request=request)


@router.post("/exam-workspace/documents/{lineage_id}/exports/{target}", response_model=VaultFile)
async def save_exam_workspace_export(
    lineage_id: UUID,
    target: ExamWorkspaceExportTarget,
    expected_revision: int,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[ExportExamWorkspaceDocumentHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> VaultFile:
    require_conversion_hub_access(registry=registry, user=user)
    return await handler.save(
        actor=user, lineage_id=lineage_id, target=target, expected_revision=expected_revision
    )


@router.post(
    "/exam-workspace/documents/{lineage_id}/items/retry",
    response_model=ExamWorkspaceItemRetryResponse,
)
async def retry_exam_workspace_item(
    lineage_id: UUID,
    request: RetryExamWorkspaceItemRequest,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RetryExamWorkspaceItemHandlerProtocol],
    user: User = Depends(require_app_ai_api),
) -> ExamWorkspaceItemRetryResponse:
    """Reconvert one question from its saved source with the chosen type."""

    require_conversion_hub_access(registry=registry, user=user)
    return await handler.handle(actor=user, lineage_id=lineage_id, request=request)


_DOCUMENT_FIELD = "document"
_DRAFT_ID_FIELD = "draft_id"
_ASSET_FIELD_PREFIX = "asset:"


@router.post(
    "/exam-workspace/guest-drafts",
    response_model=ExamWorkspaceDocumentResponse,
)
async def import_guest_exam_workspace_draft(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    handler: FromDishka[ImportGuestExamDraftHandlerProtocol],
    user: User = Depends(require_app_user_api),
) -> ExamWorkspaceDocumentResponse:
    """Save a guest's browser draft into Mina filer once per (user, draft_id)."""

    require_conversion_hub_access(registry=registry, user=user)
    draft_id, document, assets_by_id = await _read_guest_draft_request(
        request=request, settings=settings
    )
    return await handler.handle(
        actor=user, draft_id=draft_id, document=document, assets_by_id=assets_by_id
    )


async def _read_guest_draft_request(
    *, request: Request, settings: Settings
) -> tuple[UUID, NativeExamDocument, dict[str, bytes]]:
    """Parse the draft id, the document JSON and every ``asset:<id>`` file part."""

    form = await request.form()
    draft_id_values: list[str] = []
    document_values: list[str] = []
    uploaded_parts: list[tuple[str, bytes]] = []
    unknown_fields: list[str] = []
    total_bytes = 0

    for field_name, value in form.multi_items():
        if isinstance(value, StarletteUploadFile):
            content = await value.read()
            total_bytes += len(content)
            uploaded_parts.append((field_name, content))
            continue
        encoded = value.encode("utf-8")
        total_bytes += len(encoded)
        if field_name == _DRAFT_ID_FIELD:
            draft_id_values.append(value)
        elif field_name == _DOCUMENT_FIELD:
            document_values.append(value)
        else:
            unknown_fields.append(field_name)

    if total_bytes > settings.VAULT_MAX_FILE_BYTES:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Förfrågan är för stor.",
            details={
                "reason": "payload_too_large",
                "max_bytes": settings.VAULT_MAX_FILE_BYTES,
            },
        )
    if unknown_fields:
        raise validation_error(
            "Förfrågan innehåller ett okänt fält.",
            details={"reason": "unknown_field", "field": unknown_fields[0]},
        )
    if len(draft_id_values) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt ett utkast-id.",
            details={"reason": "missing_draft_id"},
        )
    if len(document_values) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt ett prov.",
            details={"reason": "missing_document"},
        )
    try:
        draft_id = UUID(draft_id_values[0])
    except ValueError as error:
        raise validation_error(
            "Utkast-id:t är inte en giltig identifierare.",
            details={"reason": "invalid_draft_id"},
        ) from error

    assets_by_id: dict[str, bytes] = {}
    for field_name, content in uploaded_parts:
        if not field_name.startswith(_ASSET_FIELD_PREFIX):
            raise validation_error(
                "Bildfiler ska skickas som asset:<bild-id>.",
                details={"reason": "unknown_field", "field": field_name},
            )
        asset_id = field_name[len(_ASSET_FIELD_PREFIX) :]
        if not asset_id or asset_id in assets_by_id:
            raise asset_mismatch_error(asset_id)
        assets_by_id[asset_id] = content

    return draft_id, parse_native_exam_document(document_values[0].encode("utf-8")), assets_by_id
