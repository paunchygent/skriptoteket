from __future__ import annotations

import io
import tarfile
from dataclasses import dataclass
from typing import Iterable


@dataclass(frozen=True, slots=True)
class WorkdirArchiveEntry:
    name: str
    content: bytes | None = None
    mode: int = 0o644
    is_dir: bool = False

    @staticmethod
    def file(*, name: str, content: bytes, mode: int = 0o644) -> "WorkdirArchiveEntry":
        return WorkdirArchiveEntry(name=name, content=content, mode=mode, is_dir=False)

    @staticmethod
    def directory(*, name: str, mode: int = 0o755) -> "WorkdirArchiveEntry":
        return WorkdirArchiveEntry(name=name, content=None, mode=mode, is_dir=True)


def build_workdir_archive_from_entries(*, entries: Iterable[WorkdirArchiveEntry]) -> bytes:
    tar_buffer = io.BytesIO()
    with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
        for entry in entries:
            info = tarfile.TarInfo(name=entry.name)
            info.mode = entry.mode
            if entry.is_dir:
                info.type = tarfile.DIRTYPE
                info.size = 0
                tar.addfile(info)
                continue

            if entry.content is None:
                raise ValueError(f"Missing content for archive entry: {entry.name}")
            info.size = len(entry.content)
            tar.addfile(info, io.BytesIO(entry.content))

    return tar_buffer.getvalue()
