from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from skriptoteket.domain.errors import ErrorDetails, validation_error
from skriptoteket.domain.scripting.file_refs import build_session_file_ref
from skriptoteket.domain.scripting.input_files import (
    InputFileEntry,
    InputManifest,
    normalize_input_files,
)
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.protocols.file_refs import FileRefResolverProtocol


@dataclass(frozen=True, slots=True)
class ResolvedRunInputs:
    files: list[ResolvedInputFile]
    manifest: InputManifest
    primary_filename: str | None
    total_size_bytes: int
    refs_by_field: dict[str, list[str]]


async def resolve_run_inputs(
    *,
    tool_id: UUID,
    user_id: UUID,
    context: str,
    input_files_by_field: dict[str, list[tuple[str, bytes]]],
    file_refs_by_field: dict[str, list[str]],
    file_ref_resolver: FileRefResolverProtocol,
) -> ResolvedRunInputs:
    upload_entries: list[ResolvedInputFile] = []
    refs_by_field: dict[str, list[str]] = {}

    for field, files in input_files_by_field.items():
        if field in file_refs_by_field and file_refs_by_field[field]:
            raise validation_error(
                "Cannot mix uploads and file refs for the same field",
                details={"field": field},
            )
        if not files:
            continue
        normalized_uploads, _ = normalize_input_files(input_files=files)
        for name, content in normalized_uploads:
            ref = build_session_file_ref(name=name)
            upload_entries.append(
                ResolvedInputFile(
                    name=name,
                    content=content,
                    ref=ref,
                    field=field,
                )
            )
            refs_by_field.setdefault(field, []).append(ref)

    resolved_refs = await file_ref_resolver.resolve_refs(
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        refs_by_field=file_refs_by_field,
    )
    for entry in resolved_refs:
        if entry.ref is None:
            raise validation_error("Resolved file ref is missing ref", details={"name": entry.name})
        refs_by_field.setdefault(entry.field, []).append(entry.ref)

    merged_files = _merge_inputs(upload_entries, resolved_refs)
    manifest = InputManifest(
        files=[
            InputFileEntry(
                name=entry.name,
                bytes=len(entry.content),
                field=entry.field,
            )
            for entry in merged_files
        ]
    )
    primary_filename = merged_files[0].name if merged_files else None
    total_size_bytes = sum(len(entry.content) for entry in merged_files)

    return ResolvedRunInputs(
        files=merged_files,
        manifest=manifest,
        primary_filename=primary_filename,
        total_size_bytes=total_size_bytes,
        refs_by_field=refs_by_field,
    )


def _merge_inputs(
    uploads: list[ResolvedInputFile],
    refs: list[ResolvedInputFile],
) -> list[ResolvedInputFile]:
    merged: list[ResolvedInputFile] = []
    seen: set[str] = set()
    collisions: dict[str, list[str]] = {}

    for entry in [*uploads, *refs]:
        if entry.name in seen:
            collisions.setdefault(entry.name, []).append(entry.name)
            continue
        seen.add(entry.name)
        merged.append(entry)

    if collisions:
        details: ErrorDetails = {
            "collisions": {safe: [safe, *originals] for safe, originals in collisions.items()}
        }
        raise validation_error(
            "Duplicate input filenames after sanitization; rename files locally.",
            details=details,
        )

    return merged
