from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.application.scripting.run_input_resolution import resolve_run_inputs
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.protocols.file_refs import FileRefEntry, FileRefResolverProtocol


class FakeFileRefResolver(FileRefResolverProtocol):
    def __init__(self, *, resolved: list[ResolvedInputFile]) -> None:
        self._resolved = resolved

    async def list_refs(
        self,
        *,
        tool_id,
        user_id,
        context,
        sources,
    ) -> list[FileRefEntry]:
        return []

    async def resolve_refs(
        self,
        *,
        tool_id,
        user_id,
        context,
        refs_by_field,
    ) -> list[ResolvedInputFile]:
        return list(self._resolved)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_run_inputs_rejects_uploads_and_refs_for_same_field() -> None:
    resolver = FakeFileRefResolver(resolved=[])

    with pytest.raises(DomainError) as exc_info:
        await resolve_run_inputs(
            tool_id=uuid4(),
            user_id=uuid4(),
            context="default",
            input_files_by_field={"documents": [("input.txt", b"data")]},
            file_refs_by_field={"documents": ["session:input.txt"]},
            file_ref_resolver=resolver,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_run_inputs_rejects_duplicate_names_across_fields() -> None:
    resolver = FakeFileRefResolver(resolved=[])

    with pytest.raises(DomainError) as exc_info:
        await resolve_run_inputs(
            tool_id=uuid4(),
            user_id=uuid4(),
            context="default",
            input_files_by_field={
                "documents": [("dup.txt", b"doc")],
                "images": [("dup.txt", b"img")],
            },
            file_refs_by_field={},
            file_ref_resolver=resolver,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_run_inputs_merges_uploads_and_refs_by_field() -> None:
    resolved_refs = [
        ResolvedInputFile(
            name="photo.png",
            content=b"\x89PNG",
            ref="session:photo.png",
            field="images",
        )
    ]
    resolver = FakeFileRefResolver(resolved=resolved_refs)

    result = await resolve_run_inputs(
        tool_id=uuid4(),
        user_id=uuid4(),
        context="default",
        input_files_by_field={"documents": [("report.txt", b"hi")]},
        file_refs_by_field={"images": ["session:photo.png"]},
        file_ref_resolver=resolver,
    )

    assert result.primary_filename == "report.txt"
    assert result.refs_by_field == {
        "documents": ["session:report.txt"],
        "images": ["session:photo.png"],
    }
    assert {entry.field for entry in result.manifest.files} == {"documents", "images"}
