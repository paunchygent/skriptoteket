from __future__ import annotations

from uuid import uuid4

import pytest

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.infrastructure.runner.run_input_storage import LocalRunInputStorage


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_run_input_storage_store_get_delete_roundtrip(tmp_path) -> None:
    storage = LocalRunInputStorage(artifacts_root=tmp_path)
    run_id = uuid4()

    files = [
        ResolvedInputFile(name="a.txt", content=b"hello", ref="session:a.txt"),
        ResolvedInputFile(name="b.bin", content=b"\x00\x01"),
    ]
    await storage.store(run_id=run_id, files=files)

    fetched = await storage.get(run_id=run_id)
    assert fetched == files

    await storage.delete(run_id=run_id)
    assert await storage.get(run_id=run_id) == []


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_run_input_storage_store_empty_raises_validation_error(tmp_path) -> None:
    storage = LocalRunInputStorage(artifacts_root=tmp_path)

    with pytest.raises(DomainError) as exc:
        await storage.store(run_id=uuid4(), files=[])

    assert exc.value.code is ErrorCode.VALIDATION_ERROR


@pytest.mark.unit
@pytest.mark.asyncio
async def test_local_run_input_storage_store_overwrites_existing_run_dir(tmp_path) -> None:
    storage = LocalRunInputStorage(artifacts_root=tmp_path)
    run_id = uuid4()

    await storage.store(
        run_id=run_id,
        files=[ResolvedInputFile(name="a.txt", content=b"v1", ref="session:a.txt")],
    )
    await storage.store(
        run_id=run_id,
        files=[
            ResolvedInputFile(name="a.txt", content=b"v2", ref="session:a.txt"),
            ResolvedInputFile(name="b.txt", content=b"x", ref="session:b.txt"),
        ],
    )

    assert await storage.get(run_id=run_id) == [
        ResolvedInputFile(name="a.txt", content=b"v2", ref="session:a.txt"),
        ResolvedInputFile(name="b.txt", content=b"x", ref="session:b.txt"),
    ]
