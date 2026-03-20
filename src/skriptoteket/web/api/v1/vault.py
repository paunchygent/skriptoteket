import mimetypes
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response

from skriptoteket.application.scripting.vault import (
    DeleteVaultFileCommand,
    DeleteVaultFileResult,
    ListVaultFilesQuery,
    ListVaultFilesResult,
    RestoreVaultFileCommand,
    RestoreVaultFileResult,
    SaveVaultFileCommand,
    SaveVaultFileResult,
)
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault import VaultListSort, VaultListState
from skriptoteket.protocols.vault import (
    DeleteVaultFileHandlerProtocol,
    DownloadVaultFileHandlerProtocol,
    ListVaultFilesHandlerProtocol,
    RestoreVaultFileHandlerProtocol,
    SaveVaultFileHandlerProtocol,
)
from skriptoteket.web.auth.api_dependencies import require_csrf_token, require_user_api
from skriptoteket.web.dishka_compat import FromDishka, inject

router = APIRouter(prefix="/api/v1/vault", tags=["vault"])


@router.get("/files", response_model=ListVaultFilesResult)
@inject
async def list_vault_files(
    handler: FromDishka[ListVaultFilesHandlerProtocol],
    user: User = Depends(require_user_api),
    state: VaultListState = Query(VaultListState.ACTIVE),
    sort: VaultListSort = Query(VaultListSort.NEWEST),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    cursor: int | None = Query(None, ge=0),
) -> ListVaultFilesResult:
    return await handler.handle(
        actor=user,
        query=ListVaultFilesQuery(
            state=state,
            sort=sort,
            search=search,
            limit=limit,
            cursor=cursor,
        ),
    )


@router.post("/files", response_model=SaveVaultFileResult)
@inject
async def save_vault_file(
    command: SaveVaultFileCommand,
    handler: FromDishka[SaveVaultFileHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> SaveVaultFileResult:
    return await handler.handle(actor=user, command=command)


@router.post("/files/{file_id}/delete", response_model=DeleteVaultFileResult)
@inject
async def delete_vault_file(
    file_id: UUID,
    handler: FromDishka[DeleteVaultFileHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> DeleteVaultFileResult:
    return await handler.handle(actor=user, command=DeleteVaultFileCommand(file_id=file_id))


@router.post("/files/{file_id}/restore", response_model=RestoreVaultFileResult)
@inject
async def restore_vault_file(
    file_id: UUID,
    handler: FromDishka[RestoreVaultFileHandlerProtocol],
    user: User = Depends(require_user_api),
    _: None = Depends(require_csrf_token),
) -> RestoreVaultFileResult:
    return await handler.handle(actor=user, command=RestoreVaultFileCommand(file_id=file_id))


@router.get("/files/{file_id}/download")
@inject
async def download_vault_file(
    file_id: UUID,
    handler: FromDishka[DownloadVaultFileHandlerProtocol],
    user: User = Depends(require_user_api),
) -> Response:
    filename, content = await handler.handle(actor=user, file_id=file_id)
    safe_filename = filename.replace('"', "")
    media_type, _ = mimetypes.guess_type(safe_filename)
    return Response(
        content=content,
        media_type=media_type or "application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename}"'},
    )
