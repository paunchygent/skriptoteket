from __future__ import annotations

import json
import shutil
from pathlib import Path
from uuid import UUID, uuid4

from skriptoteket.domain.errors import ErrorDetails, validation_error
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile
from skriptoteket.protocols.run_inputs import RunInputStorageProtocol

_META_FILENAME = "meta.json"


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

    async def store(self, *, run_id: UUID, files: list[ResolvedInputFile]) -> None:
        if not files:
            raise validation_error("files is required")

        normalized_files = _normalize_files(files=files)

        run_dir = self._run_dir(run_id=run_id)
        parent_dir = run_dir.parent
        parent_dir.mkdir(parents=True, exist_ok=True)

        temp_dir = parent_dir / f"{run_dir.name}.tmp-{uuid4()}"
        old_dir: Path | None = None

        temp_dir.mkdir(parents=True, exist_ok=False)
        try:
            for entry in normalized_files:
                (temp_dir / entry.name).write_bytes(entry.content)

            _safe_write_json(
                path=temp_dir / _META_FILENAME,
                payload={
                    "files": [
                        {"name": entry.name, "ref": entry.ref, "field": entry.field}
                        for entry in normalized_files
                    ]
                },
            )

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

    async def get(self, *, run_id: UUID) -> list[ResolvedInputFile]:
        run_dir = self._run_dir(run_id=run_id)
        if not run_dir.exists():
            return []

        meta_by_name = _load_meta(path=run_dir / _META_FILENAME)

        files: list[ResolvedInputFile] = []
        for item in sorted(run_dir.iterdir(), key=lambda path: path.name):
            if item.name == _META_FILENAME:
                continue
            if not item.is_file():
                continue
            meta = meta_by_name.get(item.name, {})
            field = meta.get("field")
            if field is None:
                raise validation_error(
                    "Run input metadata missing field ownership",
                    details={"filename": item.name, "run_id": str(run_id)},
                )
            files.append(
                ResolvedInputFile(
                    name=item.name,
                    content=item.read_bytes(),
                    ref=meta.get("ref"),
                    field=field,
                )
            )
        return files

    async def delete(self, *, run_id: UUID) -> None:
        run_dir = self._run_dir(run_id=run_id)
        if not run_dir.exists():
            return
        shutil.rmtree(run_dir, ignore_errors=True)


def _normalize_files(*, files: list[ResolvedInputFile]) -> list[ResolvedInputFile]:
    seen: set[str] = set()
    collisions: dict[str, list[str]] = {}
    normalized: list[ResolvedInputFile] = []

    for entry in files:
        name = entry.name
        if name in seen:
            collisions.setdefault(name, []).append(name)
            continue
        seen.add(name)
        normalized.append(entry)

    if collisions:
        details: ErrorDetails = {
            "collisions": {safe: [safe, *originals] for safe, originals in collisions.items()}
        }
        raise validation_error(
            "Duplicate input filenames after sanitization; rename files locally.",
            details=details,
        )

    return normalized


def _safe_write_json(*, path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = path.with_name(f"{path.name}.tmp-{uuid4()}")
    try:
        tmp_path.write_text(json.dumps(payload, ensure_ascii=False, separators=(",", ":")), "utf-8")
        tmp_path.replace(path)
    finally:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)


def _load_meta(*, path: Path) -> dict[str, dict[str, str | None]]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text("utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    if not isinstance(raw, dict):
        return {}
    raw_files = raw.get("files")
    if not isinstance(raw_files, list):
        return {}
    meta: dict[str, dict[str, str | None]] = {}
    for item in raw_files:
        if not isinstance(item, dict):
            continue
        name = item.get("name")
        ref = item.get("ref")
        field = item.get("field")
        if isinstance(name, str):
            meta[name] = {
                "ref": ref if isinstance(ref, str) else None,
                "field": field if isinstance(field, str) and field.strip() else None,
            }
    return meta
