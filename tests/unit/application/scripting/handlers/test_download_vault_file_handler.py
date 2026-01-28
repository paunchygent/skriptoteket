from __future__ import annotations

from datetime import datetime
from types import TracebackType
from uuid import UUID, uuid4

import pytest

from skriptoteket.application.scripting.handlers.download_vault_file import (
    DownloadVaultFileHandler,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.scripting.vault import (
    VaultFile,
    VaultFileSourceKind,
    VaultListSort,
    VaultListState,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol, VaultStorageProtocol
from tests.fixtures.identity_fixtures import make_user


class FakeUow(UnitOfWorkProtocol):
    async def __aenter__(self) -> UnitOfWorkProtocol:
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        return None


class FakeVaultFileRepo(VaultFileRepositoryProtocol):
    def __init__(self, file: VaultFile | None) -> None:
        self._file = file

    async def get_by_id(self, *, file_id: UUID) -> VaultFile | None:
        if self._file is None:
            return None
        return self._file if self._file.id == file_id else None

    async def list_for_user(
        self,
        *,
        user_id: UUID,
        state: VaultListState,
        search: str | None,
        sort: VaultListSort,
        limit: int,
        offset: int,
    ) -> list[VaultFile]:
        raise NotImplementedError

    async def list_active_for_user(self, *, user_id: UUID) -> list[VaultFile]:
        raise NotImplementedError

    async def list_by_ids(
        self,
        *,
        user_id: UUID,
        file_ids: list[UUID],
        include_deleted: bool,
    ) -> list[VaultFile]:
        raise NotImplementedError

    async def list_expired(self, *, cutoff: datetime, limit: int) -> list[VaultFile]:
        raise NotImplementedError

    async def create(self, *, file: VaultFile) -> VaultFile:
        raise NotImplementedError

    async def update(self, *, file: VaultFile) -> VaultFile:
        raise NotImplementedError

    async def delete(self, *, file_id: UUID) -> None:
        raise NotImplementedError


class FakeVaultStorage(VaultStorageProtocol):
    def __init__(self, *, content: bytes | None) -> None:
        self._content = content

    async def store_file(self, *, user_id: UUID, file_id: UUID, content: bytes) -> None:
        raise NotImplementedError

    async def exists_file(self, *, user_id: UUID, file_id: UUID) -> bool:
        raise NotImplementedError

    async def read_file(self, *, user_id: UUID, file_id: UUID) -> bytes:
        if self._content is None:
            raise FileNotFoundError
        return self._content

    async def delete_file(self, *, user_id: UUID, file_id: UUID) -> None:
        raise NotImplementedError


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_vault_file_returns_bytes() -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    file_id = uuid4()

    handler = DownloadVaultFileHandler(
        uow=FakeUow(),
        vault_files=FakeVaultFileRepo(
            VaultFile(
                id=file_id,
                user_id=actor.id,
                name="example.pdf",
                bytes=3,
                source_kind=VaultFileSourceKind.APP_EXPORT,
                source_run_id=None,
                source_artifact_id="chemistry.reagent_prep_chef",
                created_at=actor.created_at,
                deleted_at=None,
            )
        ),
        vault_storage=FakeVaultStorage(content=b"pdf"),
    )

    filename, content = await handler.handle(actor=actor, file_id=file_id)

    assert filename == "example.pdf"
    assert content == b"pdf"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_vault_file_returns_not_found_for_wrong_owner() -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    other_user_id = uuid4()
    file_id = uuid4()

    handler = DownloadVaultFileHandler(
        uow=FakeUow(),
        vault_files=FakeVaultFileRepo(
            VaultFile(
                id=file_id,
                user_id=other_user_id,
                name="example.pdf",
                bytes=3,
                source_kind=VaultFileSourceKind.APP_EXPORT,
                source_run_id=None,
                source_artifact_id="chemistry.reagent_prep_chef",
                created_at=actor.created_at,
                deleted_at=None,
            )
        ),
        vault_storage=FakeVaultStorage(content=b"pdf"),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, file_id=file_id)

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert exc_info.value.details.get("resource") == "VaultFile"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_download_vault_file_returns_not_found_when_bytes_missing() -> None:
    actor = make_user(role=Role.USER, user_id=uuid4())
    file_id = uuid4()

    handler = DownloadVaultFileHandler(
        uow=FakeUow(),
        vault_files=FakeVaultFileRepo(
            VaultFile(
                id=file_id,
                user_id=actor.id,
                name="example.pdf",
                bytes=3,
                source_kind=VaultFileSourceKind.APP_EXPORT,
                source_run_id=None,
                source_artifact_id="chemistry.reagent_prep_chef",
                created_at=actor.created_at,
                deleted_at=None,
            )
        ),
        vault_storage=FakeVaultStorage(content=None),
    )

    with pytest.raises(DomainError) as exc_info:
        await handler.handle(actor=actor, file_id=file_id)

    assert exc_info.value.code is ErrorCode.NOT_FOUND
    assert exc_info.value.details == {"resource": "VaultFile", "id": str(file_id)}
