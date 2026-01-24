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


async def resolve_run_inputs(
    *,
    tool_id: UUID,
    user_id: UUID,
    context: str,
    input_files: list[tuple[str, bytes]],
    file_refs: list[str],
    file_ref_resolver: FileRefResolverProtocol,
) -> ResolvedRunInputs:
    normalized_uploads: list[tuple[str, bytes]] = []
    if input_files:
        normalized_uploads, _ = normalize_input_files(input_files=input_files)

    upload_entries = [
        ResolvedInputFile(
            name=name,
            content=content,
            ref=build_session_file_ref(name=name),
        )
        for name, content in normalized_uploads
    ]
    resolved_refs = await file_ref_resolver.resolve_refs(
        tool_id=tool_id,
        user_id=user_id,
        context=context,
        refs=file_refs,
    )

    merged_files = _merge_inputs(upload_entries, resolved_refs)
    manifest = InputManifest(
        files=[InputFileEntry(name=entry.name, bytes=len(entry.content)) for entry in merged_files]
    )
    primary_filename = merged_files[0].name if merged_files else None
    total_size_bytes = sum(len(entry.content) for entry in merged_files)

    return ResolvedRunInputs(
        files=merged_files,
        manifest=manifest,
        primary_filename=primary_filename,
        total_size_bytes=total_size_bytes,
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
