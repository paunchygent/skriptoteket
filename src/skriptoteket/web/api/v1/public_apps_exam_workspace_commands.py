"""Stateless public guest command routes for the Exam Converter workspace.

Purpose:
    Let a guest run every server-side document command the shared editor uses
    on a browser-held exam: start blank, structure commands, change type,
    answer misspellings and the course catalog. No auth, no session, no storage.

Relationships:
    - Mounts under the public Exam Converter namespace and its capability gate.
    - Admits each request through the shared database limiter (GUEST_EDIT) first.
    - Delegates to the stateless ``PublicExamWorkspaceCommandHandler``, the
      deterministic misspellings handler and the profile-free catalog function.
"""

from typing import TypeVar

from fastapi import APIRouter, Request
from pydantic import BaseModel, ValidationError
from starlette.datastructures import UploadFile

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamCourseCatalogResponse,
    ExamWorkspaceLimitsResponse,
)
from skriptoteket.application.curated_apps.exam_workspace_misspellings import (
    ExamWorkspaceMisspellingsRequest,
    ExamWorkspaceMisspellingsResponse,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    exam_course_catalog_without_profile,
)
from skriptoteket.application.curated_apps.handlers.public_exam_workspace_commands import (
    PublicExamWorkspaceCommandHandler,
)
from skriptoteket.application.curated_apps.public_exam_workspace import (
    PublicAddExamChildRequest,
    PublicChangeExamItemTypeRequest,
    PublicCreateEmptyExamPartRequest,
    PublicCreateExamParentRequest,
    PublicDeleteExamParentRequest,
    PublicExamBlankResponse,
    PublicExamChangeTypeResponse,
    PublicExamCreatedPartResponse,
    PublicExamDocumentCommandResponse,
    PublicExamDocumentDeleteResponse,
    PublicExamWorkspaceDocumentRequest,
    PublicExamWorkspaceQtiImportResponse,
    PublicGroupExamItemsRequest,
    PublicMoveExamItemRequest,
    PublicReorderExamChildrenRequest,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
    ParseExamWorkspaceQtiPackageHandlerProtocol,
)
from skriptoteket.protocols.public_request_limits import (
    AdmitPublicRequestHandlerProtocol,
    PublicRequestBucket,
)
from skriptoteket.web.api.v1.public_apps import EXAM_CONVERTER_PUBLIC_API_NAMESPACE
from skriptoteket.web.api.v1.public_apps_exam_workspace_support import admit_guest_request
from skriptoteket.web.dishka_dependencies import FromDishka

router = APIRouter(
    prefix=EXAM_CONVERTER_PUBLIC_API_NAMESPACE,
    tags=["public-apps", "exam-workspace"],
)

ModelT = TypeVar("ModelT", bound=BaseModel)


async def _json_body(*, request: Request, settings: Settings, model: type[ModelT]) -> ModelT:
    """Read one JSON command body under the request size cap."""
    raw = await request.body()
    if len(raw) > settings.PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES:
        raise DomainError(
            code=ErrorCode.PAYLOAD_TOO_LARGE,
            message="Förfrågan är för stor.",
            details={
                "reason": "payload_too_large",
                "max_bytes": settings.PUBLIC_GUEST_EXAM_MAX_REQUEST_BYTES,
            },
        )
    try:
        return model.model_validate_json(raw)
    except ValidationError as error:
        raise validation_error(
            "Förfrågan är ogiltig.",
            details={"errors": error.error_count()},
        ) from error


async def _read_guest_qti_upload(
    *, request: Request, settings: Settings
) -> tuple[str, bytes, str | None]:
    """Read the one ``file`` upload and the optional ``course_key`` under the size cap."""

    form = await request.form()
    file_parts: list[tuple[str, bytes]] = []
    course_values: list[str] = []
    unknown_fields: list[str] = []
    total_bytes = 0

    for field_name, value in form.multi_items():
        if isinstance(value, UploadFile):
            content = await value.read()
            total_bytes += len(content)
            if field_name == "file":
                file_parts.append((value.filename or "prov.zip", content))
            else:
                unknown_fields.append(field_name)
            continue
        encoded = value.encode("utf-8")
        total_bytes += len(encoded)
        if field_name == "course_key":
            course_values.append(value)
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
    if len(file_parts) != 1:
        raise validation_error(
            "Förfrågan måste innehålla exakt en QTI-fil.",
            details={"reason": "missing_file"},
        )
    filename, content = file_parts[0]
    course_key = course_values[0] if course_values else None
    return filename, content, course_key or None


@router.post("/workspace/blank", response_model=PublicExamBlankResponse)
async def blank_public_exam_workspace(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamBlankResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    return handler.blank()


@router.post("/workspace/imports/qti", response_model=PublicExamWorkspaceQtiImportResponse)
async def import_public_exam_workspace_qti_package(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[ParseExamWorkspaceQtiPackageHandlerProtocol],
) -> PublicExamWorkspaceQtiImportResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_IMPORT,
    )
    filename, content, course_key = await _read_guest_qti_upload(request=request, settings=settings)
    container = handler.handle(filename=filename, content=content, course_key=course_key)
    return PublicExamWorkspaceQtiImportResponse(
        document=container.document,
        assets_by_id=container.assets_by_id,
        notes=container.notes,
    )


@router.post("/workspace/parents", response_model=PublicExamDocumentCommandResponse)
async def create_public_exam_workspace_parent(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamDocumentCommandResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(request=request, settings=settings, model=PublicCreateExamParentRequest)
    return handler.create_parent(
        document=body.document,
        instruction=body.instruction,
        child=body.child,
        position=body.position,
    )


@router.post("/workspace/parents/group", response_model=PublicExamCreatedPartResponse)
async def group_public_exam_workspace_items(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamCreatedPartResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(request=request, settings=settings, model=PublicGroupExamItemsRequest)
    return handler.group_items(document=body.document, item_ids=body.item_ids)


@router.post("/workspace/parents/empty", response_model=PublicExamCreatedPartResponse)
async def create_public_exam_workspace_empty_part(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamCreatedPartResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(
        request=request, settings=settings, model=PublicCreateEmptyExamPartRequest
    )
    return handler.create_empty_part(document=body.document, position=body.position)


@router.post("/workspace/parents/move", response_model=PublicExamDocumentCommandResponse)
async def move_public_exam_workspace_item(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamDocumentCommandResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(request=request, settings=settings, model=PublicMoveExamItemRequest)
    return handler.move_item(
        document=body.document, item_id=body.item_id, target_parent_id=body.target_parent_id
    )


@router.post(
    "/workspace/parents/{parent_id}/children",
    response_model=PublicExamDocumentCommandResponse,
)
async def add_public_exam_workspace_child(
    parent_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamDocumentCommandResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(request=request, settings=settings, model=PublicAddExamChildRequest)
    return handler.add_child(
        document=body.document, parent_id=parent_id, child=body.child, position=body.position
    )


@router.post(
    "/workspace/parents/{parent_id}/children/{item_id}/delete",
    response_model=PublicExamDocumentDeleteResponse,
)
async def delete_public_exam_workspace_child(
    parent_id: str,
    item_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamDocumentDeleteResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(
        request=request, settings=settings, model=PublicExamWorkspaceDocumentRequest
    )
    return handler.delete_child(document=body.document, parent_id=parent_id, item_id=item_id)


@router.post(
    "/workspace/parents/{parent_id}/children/order",
    response_model=PublicExamDocumentCommandResponse,
)
async def reorder_public_exam_workspace_children(
    parent_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamDocumentCommandResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(
        request=request, settings=settings, model=PublicReorderExamChildrenRequest
    )
    return handler.reorder_children(
        document=body.document, parent_id=parent_id, item_ids=body.item_ids
    )


@router.post(
    "/workspace/parents/{parent_id}/delete",
    response_model=PublicExamDocumentDeleteResponse,
)
async def delete_public_exam_workspace_parent(
    parent_id: str,
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamDocumentDeleteResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(request=request, settings=settings, model=PublicDeleteExamParentRequest)
    return handler.delete_parent(document=body.document, parent_id=parent_id, mode=body.mode)


@router.post("/workspace/change-type", response_model=PublicExamChangeTypeResponse)
async def change_public_exam_workspace_item_type(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[PublicExamWorkspaceCommandHandler],
) -> PublicExamChangeTypeResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(
        request=request, settings=settings, model=PublicChangeExamItemTypeRequest
    )
    return handler.change_type(
        document=body.document, item_id=body.item_id, target_kind=body.target_kind
    )


@router.post(
    "/workspace/answer-misspellings",
    response_model=ExamWorkspaceMisspellingsResponse,
)
async def answer_public_exam_workspace_misspellings(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
    handler: FromDishka[GenerateExamWorkspaceMisspellingsHandlerProtocol],
) -> ExamWorkspaceMisspellingsResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(
        request=request, settings=settings, model=ExamWorkspaceMisspellingsRequest
    )
    return handler.handle(request=body)


@router.get("/workspace/limits", response_model=ExamWorkspaceLimitsResponse)
async def get_public_exam_workspace_limits(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
) -> ExamWorkspaceLimitsResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    return ExamWorkspaceLimitsResponse(max_exam_bytes=settings.VAULT_MAX_FILE_BYTES)


@router.get("/workspace/courses", response_model=ExamCourseCatalogResponse)
async def get_public_exam_course_catalog(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    settings: FromDishka[Settings],
    admit_handler: FromDishka[AdmitPublicRequestHandlerProtocol],
) -> ExamCourseCatalogResponse:
    await admit_guest_request(
        request=request,
        registry=registry,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    return exam_course_catalog_without_profile()
