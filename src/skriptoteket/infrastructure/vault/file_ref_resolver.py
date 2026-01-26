from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.file_refs import (
    FileRef,
    FileRefSource,
    build_vault_file_ref,
    parse_file_ref,
)
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.protocols.file_refs import FileRefEntry, FileRefResolverProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol


class VaultFileRefResolver(FileRefResolverProtocol):
    def __init__(
        self,
        *,
        vault_files: VaultFileRepositoryProtocol,
        vault_storage: VaultStorageProtocol,
    ) -> None:
        self._vault_files = vault_files
        self._vault_storage = vault_storage

    async def list_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        sources: list[FileRefSource],
    ) -> list[FileRefEntry]:
        del tool_id, context
        if FileRefSource.VAULT not in sources:
            return []
        files = await self._vault_files.list_active_for_user(user_id=user_id)
        return [
            FileRefEntry(
                ref=build_vault_file_ref(file_id=item.id),
                name=item.name,
                bytes=item.bytes,
                field=None,
            )
            for item in files
        ]

    async def resolve_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        refs_by_field: dict[str, list[FileRef]],
    ) -> list[ResolvedInputFile]:
        del tool_id, context
        if not refs_by_field:
            return []

        normalized: list[tuple[str, FileRef, UUID]] = []
        seen_ids: set[UUID] = set()
        duplicates: list[str] = []

        for field, refs in refs_by_field.items():
            for ref in refs:
                source, value = parse_file_ref(value=ref)
                if source is not FileRefSource.VAULT:
                    raise validation_error(
                        "Only vault file refs are supported here.",
                        details={"ref": ref},
                    )
                file_id = UUID(value)
                if file_id in seen_ids:
                    duplicates.append(str(file_id))
                    continue
                seen_ids.add(file_id)
                normalized.append((field, ref, file_id))

        if duplicates:
            raise validation_error(
                "Duplicate file refs are not allowed.",
                details={"refs": duplicates},
            )

        files = await self._vault_files.list_by_ids(
            user_id=user_id,
            file_ids=[file_id for _, _, file_id in normalized],
            include_deleted=False,
        )
        by_id = {item.id: item for item in files}

        missing = [str(file_id) for _, _, file_id in normalized if file_id not in by_id]
        if missing:
            raise validation_error(
                "Requested vault files are not available.",
                details={"missing": missing},
            )

        resolved: list[ResolvedInputFile] = []
        missing_content: list[str] = []
        for field, ref, file_id in normalized:
            vault_file = by_id[file_id]
            try:
                content = await self._vault_storage.read_file(
                    user_id=user_id,
                    file_id=vault_file.id,
                )
            except FileNotFoundError:
                missing_content.append(str(file_id))
                continue
            resolved.append(
                ResolvedInputFile(
                    name=vault_file.name,
                    content=content,
                    ref=ref,
                    field=field,
                )
            )

        if missing_content:
            raise validation_error(
                "Requested vault files are not available.",
                details={"missing": missing_content},
            )

        return resolved
