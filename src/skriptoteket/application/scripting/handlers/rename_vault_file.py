from __future__ import annotations

from pathlib import PurePosixPath

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentSummary
from skriptoteket.application.curated_apps.handlers.exam_workspace_document_store import (
    EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX,
)
from skriptoteket.application.scripting.handlers._vault_helpers import build_vault_file_info
from skriptoteket.application.scripting.vault import RenameVaultFileCommand, RenameVaultFileResult
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.vault_names import rename_vault_filename
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import RenameVaultFileHandlerProtocol, VaultFileRepositoryProtocol


class RenameVaultFileHandler(RenameVaultFileHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        vault_files: VaultFileRepositoryProtocol,
        index: ExamIndexRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._vault_files = vault_files
        self._index = index

    async def handle(
        self, *, actor: User, command: RenameVaultFileCommand
    ) -> RenameVaultFileResult:
        async with self._uow:
            await self._vault_files.lock_owner_renames(user_id=actor.id)
            target = await self._vault_files.get_by_id(file_id=command.file_id)
            if target is None or target.user_id != actor.id or target.deleted_at is not None:
                raise not_found("VaultFile", str(command.file_id))
            if target.document_lineage_id is not None:
                await self._vault_files.lock_document_lineage(
                    user_id=actor.id, document_lineage_id=target.document_lineage_id
                )
            extension = (
                ".provdokument.zip"
                if target.document_lineage_id is not None
                and target.export_format is None
                and target.source_artifact_id is not None
                and target.source_artifact_id.startswith(EXAM_WORKSPACE_SOURCE_ARTIFACT_PREFIX)
                else PurePosixPath(target.name).suffix
            )
            name = rename_vault_filename(stem=command.stem, extension=extension)
            if await self._vault_files.name_in_use(
                user_id=actor.id,
                name=name,
                exclude_lineage_id=target.document_lineage_id
                if target.export_format is None
                else None,
                exclude_file_id=target.id,
            ):
                raise validation_error(
                    "Namnet används redan av en annan fil.",
                    details={"code": "vault_name_in_use", "name": name, "file_id": str(target.id)},
                )
            active = await self._vault_files.rename_active(
                user_id=actor.id, file_id=target.id, name=name
            )
            if active is None:
                raise not_found("VaultFile", str(command.file_id))
            renamed = (
                await self._vault_files.rename_lineage(
                    user_id=actor.id, document_lineage_id=target.document_lineage_id, name=name
                )
                if target.document_lineage_id is not None and target.export_format is None
                else [active]
            )
            exam = (
                None
                if target.document_lineage_id is None
                else await self._index.get(
                    owner_user_id=actor.id, lineage_id=target.document_lineage_id
                )
            )
            summary = (
                None
                if exam is None
                else ExamWorkspaceDocumentSummary(
                    lineage_id=exam.lineage_id,
                    version=exam.version,
                    vault_file_id=exam.head_vault_file_id,
                    name=exam.name,
                    saved_at=exam.saved_at,
                    title=exam.title,
                    course_key=exam.course_key,
                )
            )
        return RenameVaultFileResult(
            file=build_vault_file_info(vault_file=active),
            renamed_file_ids=tuple(version.id for version in renamed),
            exam_summary=summary,
        )
