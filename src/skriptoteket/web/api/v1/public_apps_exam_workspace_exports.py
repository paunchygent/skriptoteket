"""Stateless public guest export routes for the Exam Converter workspace.

Purpose:
  Let a guest send a native exam document plus its picture bytes and receive the
  QTI package, print PDF, DOCX or Exam.net import checklist rendered by the same
  code the signed-in workspace export uses.

Relationships:
  - Mounts under the public Exam Converter namespace and its capability gate.
  - Admits each request through the shared database limiter before reading input.
  - Delegates rendering to ``PublicExamWorkspaceExportHandler``.
"""

from fastapi import APIRouter, Request, Response
from starlette.datastructures import UploadFile

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceExportChecklistResponse,
    ExamWorkspaceExportTarget,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_exports import (
    PublicExamWorkspaceExportHandler,
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
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestBucket,
)
from skriptoteket.web.api.v1.public_apps import EXAM_CONVERTER_PUBLIC_API_NAMESPACE
from skriptoteket.web.api.v1.public_apps_exam_workspace_support import admit_guest_request
from skriptoteket.web.content_disposition import attachment_content_disposition
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
    tags=["public-apps", "exam-workspace"],
)

_DOCUMENT_FIELD = "document"
_ASSET_FIELD_PREFIX = "asset:"


@router.post("/workspace/exports/{target}")
async def export_public_exam_workspace_document(
    target: ExamWorkspaceExportTarget,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceExportHandler],
) -> Response:
    await admit_guest_request(
        request=request,
        registry=registry,
        settings=settings,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EXPORT,
    )
    document, assets_by_id = await _read_guest_document_request(request=request, settings=settings)
    result = handler.render(document=document, assets_by_id=assets_by_id, target=target)
    return Response(
        content=result.content,
        media_type=result.media_type,
        headers={"Content-Disposition": attachment_content_disposition(filename=result.filename)},
    )


@router.post(
    "/workspace/export-checklist",
    response_model=ExamWorkspaceExportChecklistResponse,
)
async def export_public_exam_workspace_document_checklist(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceExportHandler],
) -> ExamWorkspaceExportChecklistResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        settings=settings,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EXPORT,
    )
    document, assets_by_id = await _read_guest_document_request(request=request, settings=settings)
    return handler.checklist(document=document, assets_by_id=assets_by_id)


async def _read_guest_document_request(
    *, request: Request, settings: Settings
) -> tuple[NativeExamDocument, dict[str, bytes]]:
    """Parse the document JSON and every ``asset:<id>`` part under the request size cap."""

    form = await request.form()
    document_values: list[str] = []
    uploaded_parts: list[tuple[str, bytes]] = []
    unknown_fields: list[str] = []
    total_bytes = 0

    for field_name, value in form.multi_items():
        if isinstance(value, UploadFile):
            content = await value.read()
            total_bytes += len(content)
            uploaded_parts.append((field_name, content))
            continue
        encoded = value.encode("utf-8")
        total_bytes += len(encoded)
        if field_name == _DOCUMENT_FIELD:
            document_values.append(value)
        else:
            unknown_fields.append(field_name)

    if total_bytes > settings.PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Förfrågan är för stor.",
            details={
                "reason": "payload_too_large",
                "max_bytes": settings.PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES,
            },
        )
    if unknown_fields:
        raise validation_error(
            "Förfrågan innehåller ett okänt fält.",
            details={"reason": "unknown_field", "field": unknown_fields[0]},
        )
    if len(document_values) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt ett prov.",
            details={"reason": "missing_document"},
        )

    assets_by_id: dict[str, bytes] = {}
    for field_name, content in uploaded_parts:
        asset_id = (
            field_name[len(_ASSET_FIELD_PREFIX) :]
            if field_name.startswith(_ASSET_FIELD_PREFIX)
            else field_name
        )
        if not asset_id or asset_id in assets_by_id:
            raise asset_mismatch_error(asset_id)
        assets_by_id[asset_id] = content

    return (
        parse_native_exam_document(document_values[0].encode("utf-8")),
        assets_by_id,
    )
