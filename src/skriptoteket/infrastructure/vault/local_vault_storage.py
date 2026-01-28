from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.protocols.vault import VaultStorageProtocol


class LocalVaultStorage(VaultStorageProtocol):
    """Filesystem-backed vault storage."""

    def __init__(self, *, vault_root: Path) -> None:
        self._vault_root = vault_root

    def _file_path(self, *, user_id: UUID, file_id: UUID) -> Path:
        return self._vault_root / str(user_id) / str(file_id)

    async def store_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
        content: bytes,
    ) -> None:
        target_path = self._file_path(user_id=user_id, file_id=file_id)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        tmp_path = target_path.with_name(f"{target_path.name}.tmp-{uuid4()}")
        try:
            tmp_path.write_bytes(content)
            tmp_path.replace(target_path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

    async def exists_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> bool:
        return self._file_path(user_id=user_id, file_id=file_id).is_file()

    async def read_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> bytes:
        path = self._file_path(user_id=user_id, file_id=file_id)
        if not path.is_file():
            raise FileNotFoundError(path)
        return path.read_bytes()

    async def delete_file(
        self,
        *,
        user_id: UUID,
        file_id: UUID,
    ) -> None:
        path = self._file_path(user_id=user_id, file_id=file_id)
        if not path.exists():
            return
        if path.is_file():
            path.unlink(missing_ok=True)
            return
        if path.is_dir():
            shutil.rmtree(path, ignore_errors=True)
