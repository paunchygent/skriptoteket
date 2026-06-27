"""Document Converter project preview API routes.

Purpose:
    Expose route-inactive HTML/CSS project preview rendering, status,
    download, discard, and explicit Mina filer save contracts under the scoped
    Conversion Hub Document Converter namespace.

Relationships:
    Uses application project preview handlers and shared Conversion Hub app
    access checks while keeping production SPA route activation out of scope.
"""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, Request, UploadFile
from fastapi.responses import Response

from skriptoteket.application.curated_apps.document_converter_projects import (
    DiscardDocumentConverterProjectPreviewResult,
    DocumentConverterProjectManifest,
    DocumentConverterProjectPreviewResult,
    DocumentConverterProjectUploadedFile,
    SaveDocumentConverterProjectPreviewArtifactResult,
    validate_document_converter_project_upload,
)
from skriptoteket.application.curated_apps.handlers.document_converter_project_previews import (
    DiscardDocumentConverterProjectPreviewHandler,
    DownloadDocumentConverterProjectPreviewArtifactHandler,
    GetDocumentConverterProjectPreviewHandler,
    RenderDocumentConverterProjectPreviewHandler,
    SaveDocumentConverterProjectPreviewArtifactHandler,
)
from skriptoteket.config import Settings
from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.curated_apps import CuratedAppRegistryProtocol
from skriptoteket.web.api.v1.apps_conversion_hub_access import (
    APP_ID,
    require_conversion_hub_access,
)
from skriptoteket.web.auth.huleedu_app_projection import require_app_user_api
from skriptoteket.web.dishka_dependencies import FromDishka
from skriptoteket.web.uploads import read_upload_files

router = APIRouter(
    prefix=f"/api/v1/apps/{APP_ID}/document-converter/project-previews",
    tags=["apps"],
)

_PDF_BINARY_RESPONSE = {
    "description": "Document Converter project preview PDF artifact.",
    "content": {
        "application/pdf": {
            "schema": {
                "type": "string",
                "format": "binary",
            }
        }
    },
}


def _require_app_access(*, registry: CuratedAppRegistryProtocol, user: User) -> None:
    require_conversion_hub_access(registry=registry, user=user)


@router.post("", response_model=DocumentConverterProjectPreviewResult)
async def render_document_converter_project_preview(
    request: Request,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[RenderDocumentConverterProjectPreviewHandler],
    settings: FromDishka[Settings],
    manifest_json: str = Form(..., min_length=2),
    files: list[UploadFile] = File(...),
    user: User = Depends(require_app_user_api),
) -> DocumentConverterProjectPreviewResult:
    """Render one temporary project preview under the scoped app namespace."""
    del request
    _require_app_access(registry=registry, user=user)
    manifest = _parse_manifest(manifest_json=manifest_json)
    project_files = await _read_project_files(
        manifest=manifest,
        files=files,
        settings=settings,
    )
    return await handler.handle(actor=user, manifest=manifest, files=project_files)


@router.get("/{preview_id}", response_model=DocumentConverterProjectPreviewResult)
async def get_document_converter_project_preview(
    preview_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[GetDocumentConverterProjectPreviewHandler],
    user: User = Depends(require_app_user_api),
) -> DocumentConverterProjectPreviewResult:
    """Return owner-scoped temporary project preview status."""
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, preview_id=preview_id)


@router.get(
    "/{preview_id}/artifacts/{artifact_id}",
    response_class=Response,
    responses={200: _PDF_BINARY_RESPONSE},
)
async def download_document_converter_project_preview_artifact(
    preview_id: UUID,
    artifact_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[DownloadDocumentConverterProjectPreviewArtifactHandler],
    filename_stem: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    user: User = Depends(require_app_user_api),
) -> Response:
    """Download one server-authorized temporary project preview artifact."""
    _require_app_access(registry=registry, user=user)
    artifact = await handler.handle(
        actor=user,
        preview_id=preview_id,
        artifact_id=artifact_id,
        filename_stem=filename_stem,
    )
    return Response(
        content=artifact.content,
        media_type=artifact.content_type,
        headers={
            "Content-Disposition": f'attachment; filename="{artifact.filename}"',
            "Cache-Control": "no-store",
        },
    )


@router.post(
    "/{preview_id}/artifacts/{artifact_id}/save",
    response_model=SaveDocumentConverterProjectPreviewArtifactResult,
)
async def save_document_converter_project_preview_artifact(
    preview_id: UUID,
    artifact_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[SaveDocumentConverterProjectPreviewArtifactHandler],
    filename_stem: Annotated[str | None, Query(min_length=1, max_length=255)] = None,
    user: User = Depends(require_app_user_api),
) -> SaveDocumentConverterProjectPreviewArtifactResult:
    """Save one explicit temporary preview artifact into Mina filer."""
    _require_app_access(registry=registry, user=user)
    return await handler.handle(
        actor=user,
        preview_id=preview_id,
        artifact_id=artifact_id,
        filename_stem=filename_stem,
    )


@router.delete("/{preview_id}", response_model=DiscardDocumentConverterProjectPreviewResult)
async def discard_document_converter_project_preview(
    preview_id: UUID,
    registry: FromDishka[CuratedAppRegistryProtocol],
    handler: FromDishka[DiscardDocumentConverterProjectPreviewHandler],
    user: User = Depends(require_app_user_api),
) -> DiscardDocumentConverterProjectPreviewResult:
    """Discard one temporary project preview and remove artifact authority."""
    _require_app_access(registry=registry, user=user)
    return await handler.handle(actor=user, preview_id=preview_id)


def _parse_manifest(*, manifest_json: str) -> DocumentConverterProjectManifest:
    try:
        return DocumentConverterProjectManifest.model_validate_json(manifest_json)
    except Exception as exc:
        raise validation_error("Invalid Document Converter project manifest JSON.") from exc


async def _read_project_files(
    *,
    manifest: DocumentConverterProjectManifest,
    files: list[UploadFile],
    settings: Settings,
) -> list[DocumentConverterProjectUploadedFile]:
    validated = _validate_project_uploads(manifest=manifest, files=files)
    input_files = await read_upload_files(
        files=files,
        max_files=manifest.expected_file_count,
        max_file_bytes=settings.UPLOAD_MAX_FILE_BYTES,
        max_total_bytes=settings.UPLOAD_MAX_TOTAL_BYTES,
        default_filename="document-converter-project-file.bin",
    )
    return [
        DocumentConverterProjectUploadedFile(
            filename=validated[index][0],
            content_type=validated[index][1],
            content=input_file[1],
        )
        for index, input_file in enumerate(input_files)
    ]


def _validate_project_uploads(
    *,
    manifest: DocumentConverterProjectManifest,
    files: list[UploadFile],
) -> list[tuple[str, str]]:
    validated = [
        validate_document_converter_project_upload(
            manifest=manifest,
            filename=upload.filename,
            content_type=upload.content_type,
        )
        for upload in files
    ]
    filenames = [filename for filename, _content_type in validated]
    if len(filenames) != len(set(filenames)):
        raise validation_error("Document Converter project uploads contain duplicate filenames.")
    manifest.validate_uploaded_file_set(uploaded_filenames=set(filenames))
    return validated
