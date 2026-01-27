from __future__ import annotations

from pathlib import Path
from uuid import UUID

from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.infrastructure.artifacts.filesystem import build_artifacts_manifest
from skriptoteket.infrastructure.runner.path_safety import validate_output_path


class CuratedAppArtifactWriter:
    def __init__(self, *, artifacts_root: Path, run_id: UUID) -> None:
        self._artifacts_root = artifacts_root
        self._run_id = run_id
        self._run_dir = artifacts_root / str(run_id)
        self._initialized = False

    def _ensure_run_dir(self) -> None:
        if self._initialized:
            return
        self._run_dir.mkdir(parents=True, exist_ok=False)
        self._initialized = True

    def write_bytes(self, *, output_path: str, content: bytes) -> None:
        self._ensure_run_dir()

        relative_path = Path(validate_output_path(path=output_path).as_posix())
        candidate_path = (self._run_dir / relative_path).resolve()

        run_root = self._run_dir.resolve()
        artifacts_root = self._artifacts_root.resolve()
        if run_root not in candidate_path.parents:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Artifact path is outside run directory",
                details={"path": output_path},
            )
        if artifacts_root not in candidate_path.parents:
            raise DomainError(
                code=ErrorCode.INTERNAL_ERROR,
                message="Artifact path is outside artifacts root",
                details={"path": output_path},
            )

        candidate_path.parent.mkdir(parents=True, exist_ok=True)
        candidate_path.write_bytes(content)

    def build_manifest(self) -> ArtifactsManifest:
        if not self._initialized:
            return ArtifactsManifest(artifacts=[])
        return build_artifacts_manifest(run_dir=self._run_dir)
