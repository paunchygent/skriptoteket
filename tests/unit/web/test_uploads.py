from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.web.uploads import read_upload_files


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_upload_files_rejects_action_json_reserved_filename() -> None:
    with pytest.raises(DomainError) as exc_info:
        await read_upload_files(
            files=[UploadFile(BytesIO(b"{}"), filename="action.json")],
            max_files=10,
            max_file_bytes=10,
            max_total_bytes=10,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_upload_files_rejects_action_json_even_with_whitespace() -> None:
    with pytest.raises(DomainError) as exc_info:
        await read_upload_files(
            files=[UploadFile(BytesIO(b"{}"), filename=" action.json ")],
            max_files=10,
            max_file_bytes=10,
            max_total_bytes=10,
        )

    assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
