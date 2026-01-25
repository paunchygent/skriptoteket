from __future__ import annotations

from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.session_files.file_ref_resolver import SessionFileRefResolver
from skriptoteket.protocols.session_files import SessionFileContent, SessionFileStorageProtocol


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_refs_rejects_duplicate_refs() -> None:
    session_files = AsyncMock(spec=SessionFileStorageProtocol)
    session_files.get_files_by_name.return_value = []

    resolver = SessionFileRefResolver(session_files=session_files)

    with pytest.raises(DomainError) as exc_info:
        await resolver.resolve_refs(
            tool_id=uuid4(),
            user_id=uuid4(),
            context="default",
            refs_by_field={"documents": ["session:dup.txt", "session:dup.txt"]},
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details["refs"] == ["dup.txt"]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_resolve_refs_rejects_field_mismatch() -> None:
    session_files = AsyncMock(spec=SessionFileStorageProtocol)
    session_files.get_files_by_name.return_value = [
        SessionFileContent(name="doc.txt", content=b"data", field="images")
    ]

    resolver = SessionFileRefResolver(session_files=session_files)

    with pytest.raises(DomainError) as exc_info:
        await resolver.resolve_refs(
            tool_id=uuid4(),
            user_id=uuid4(),
            context="default",
            refs_by_field={"documents": ["session:doc.txt"]},
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
    assert exc_info.value.details["mismatched"] == ["doc.txt"]
