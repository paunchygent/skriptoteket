from __future__ import annotations

from uuid import UUID

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.file_refs import (
    FileRef,
    build_session_file_ref,
    parse_file_ref,
)
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.protocols.file_refs import FileRefEntry, FileRefResolverProtocol
from skriptoteket.protocols.session_files import SessionFileStorageProtocol


class SessionFileRefResolver(FileRefResolverProtocol):
    def __init__(self, *, session_files: SessionFileStorageProtocol) -> None:
        self._session_files = session_files

    async def list_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
    ) -> list[FileRefEntry]:
        files = await self._session_files.list_files(
            tool_id=tool_id,
            user_id=user_id,
            context=context,
        )
        return [
            FileRefEntry(
                ref=build_session_file_ref(name=item.name),
                name=item.name,
                bytes=item.bytes,
                field=item.field,
            )
            for item in files
            if item.field is not None
        ]

    async def resolve_refs(
        self,
        *,
        tool_id: UUID,
        user_id: UUID,
        context: str,
        refs_by_field: dict[str, list[FileRef]],
    ) -> list[ResolvedInputFile]:
        if not refs_by_field:
            return []

        normalized: list[tuple[str, FileRef, str]] = []
        seen_names: set[str] = set()
        duplicates: list[str] = []

        for field, refs in refs_by_field.items():
            for ref in refs:
                source, value = parse_file_ref(value=ref)
                if source != "session":
                    raise validation_error(
                        "Only session file refs are supported right now.",
                        details={"ref": ref},
                    )
                if value in seen_names:
                    duplicates.append(value)
                    continue
                seen_names.add(value)
                normalized.append((field, ref, value))

        if duplicates:
            raise validation_error(
                "Duplicate file refs are not allowed.",
                details={"refs": duplicates},
            )

        files = await self._session_files.get_files_by_name(
            tool_id=tool_id,
            user_id=user_id,
            context=context,
            names=[name for _, _, name in normalized],
        )
        by_name = {item.name: item for item in files}

        missing = [name for _, _, name in normalized if name not in by_name]
        if missing:
            raise validation_error(
                "Requested session files are not available.",
                details={"missing": missing},
            )

        mismatched: list[str] = []
        resolved: list[ResolvedInputFile] = []
        for field, ref, name in normalized:
            stored = by_name[name]
            if stored.field != field:
                mismatched.append(name)
                continue
            resolved.append(
                ResolvedInputFile(
                    name=name,
                    content=stored.content,
                    ref=ref,
                    field=field,
                )
            )

        if mismatched:
            raise validation_error(
                "Requested session files are not available for the selected field.",
                details={"mismatched": mismatched},
            )

        return resolved
