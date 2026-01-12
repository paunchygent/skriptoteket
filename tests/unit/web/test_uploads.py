from __future__ import annotations

from io import BytesIO

import pytest
from fastapi import UploadFile

from skriptoteket.web.uploads import read_upload_files


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_upload_files_allows_action_json_filename() -> None:
    input_files = await read_upload_files(
        files=[UploadFile(BytesIO(b"{}"), filename="action.json")],
        max_files=10,
        max_file_bytes=10,
        max_total_bytes=10,
    )

    assert input_files == [("action.json", b"{}")]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_read_upload_files_allows_action_json_even_with_whitespace() -> None:
    input_files = await read_upload_files(
        files=[UploadFile(BytesIO(b"{}"), filename=" action.json ")],
        max_files=10,
        max_file_bytes=10,
        max_total_bytes=10,
    )

    assert input_files == [(" action.json ", b"{}")]
