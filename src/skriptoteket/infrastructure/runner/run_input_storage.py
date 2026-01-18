from __future__ import annotations

import shutil
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.domain.errors import validation_error
from skriptoteket.domain.scripting.input_files import normalize_input_files
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol
from skriptoteket.protocols.session_files import InputFile


class LocalRunInputStorage(RunInputStorageProtocol):
    """Filesystem-backed storage for per-run input files.

    Layout:
      {artifacts_root}/run-inputs/{run_id}/

    This is intentionally separate from the output artifacts directory
    ({artifacts_root}/{run_id}/) to avoid collisions with artifact extraction.
    """

    def __init__(self, *, artifacts_root: Path) -> None:
        self._root = artifacts_root / "run-inputs"

    def _run_dir(self, *, run_id: UUID) -> Path:
        return self._root / str(run_id)

    async def store(self, *, run_id: UUID, files: list[InputFile]) -> None:
        if not files:
            raise validation_error("files is required")

        normalized_files = normalize_input_files(input_files=files)[0]

        run_dir = self._run_dir(run_id=run_id)
        parent_dir = run_dir.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = parent_dir / f"{run_dir.name}.tmp-{uuid4()}"
        old_dir: Path | None = None

        temp_dir.mkdir(parents=True, exist_ok=False)
        try:
            for name, content in normalized_files:
                (temp_dir / name).write_bytes(content)

            if run_dir.exists():
                old_dir = parent_dir / f"{run_dir.name}.old-{uuid4()}"
                run_dir.rename(old_dir)

            temp_dir.rename(run_dir)
        except Exception:
            shutil.rmtree(temp_dir, ignore_errors=True)
            if old_dir is not None and not run_dir.exists():
                try:
                    old_dir.rename(run_dir)
                except OSError:
                    pass
            raise
        finally:
            if old_dir is not None:
                shutil.rmtree(old_dir, ignore_errors=True)

    async def get(self, *, run_id: UUID) -> list[InputFile]:
        run_dir = self._run_dir(run_id=run_id)
        if not run_dir.exists():
            return []

        files: list[InputFile] = []
        for item in sorted(run_dir.iterdir(), key=lambda path: path.name):
            if not item.is_file():
                continue
            files.append((item.name, item.read_bytes()))
        return files

    async def delete(self, *, run_id: UUID) -> None:
        run_dir = self._run_dir(run_id=run_id)
        if not run_dir.exists():
            return
        shutil.rmtree(run_dir, ignore_errors=True)
