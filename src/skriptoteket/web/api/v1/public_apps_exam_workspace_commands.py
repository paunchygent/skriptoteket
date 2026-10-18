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

from __future__ import annotations

from typing import TypeVar

from fastapi import APIRouter, Request
from pydantic import BaseModel, ValidationError

from skriptoteket.application.curated_apps.exam_workspace import ExamCourseCatalogResponse
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
    PublicCreateExamParentRequest,
    PublicDeleteExamParentRequest,
    PublicExamBlankResponse,
    PublicExamChangeTypeResponse,
    PublicExamDocumentCommandResponse,
    PublicExamDocumentDeleteResponse,
    PublicExamWorkspaceDocumentRequest,
    PublicReorderExamChildrenRequest,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import DomainError, ErrorCode, validation_error
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.protocols.exam_workspace import (
    GenerateExamWorkspaceMisspellingsHandlerProtocol,
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
        settings=settings,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    return handler.blank()


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
        settings=settings,
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
        settings=settings,
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
        settings=settings,
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
        settings=settings,
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
        settings=settings,
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
        settings=settings,
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
        settings=settings,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    body = await _json_body(
        request=request, settings=settings, model=ExamWorkspaceMisspellingsRequest
    )
    return handler.handle(request=body)


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
        settings=settings,
        admit_handler=admit_handler,
        bucket=PublicRequestBucket.GUEST_EDIT,
    )
    return exam_course_catalog_without_profile()
