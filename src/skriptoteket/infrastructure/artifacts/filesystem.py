from __future__ import annotations

import re
from pathlib import Path

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, StoredArtifact
from skriptoteket.infrastructure.runner.path_safety import validate_output_path


def build_artifacts_manifest(*, run_dir: Path) -> ArtifactsManifest:
    output_dir = run_dir / "output"
    if not output_dir.exists():
        return ArtifactsManifest(artifacts=[])

    artifacts: list[StoredArtifact] = []
    used_ids: set[str] = set()

    for file_path in sorted(output_dir.rglob("*")):
        if not file_path.is_file():
            continue

        relative_path = file_path.relative_to(run_dir).as_posix()
        validate_output_path(path=relative_path)

        artifact_id = _slugify_artifact_id(relative_path)
        if artifact_id in used_ids:
            suffix = 2
            while f"{artifact_id}_{suffix}" in used_ids:
                suffix += 1
            artifact_id = f"{artifact_id}_{suffix}"
        used_ids.add(artifact_id)

        artifacts.append(
            StoredArtifact(
                artifact_id=artifact_id,
                path=relative_path,
                bytes=file_path.stat().st_size,
            )
        )

    return ArtifactsManifest(artifacts=artifacts)


def _slugify_artifact_id(path: str) -> str:
    normalized = path.strip().lower()
    normalized = re.sub(r"[^a-z0-9]+", "_", normalized).strip("_")
    return normalized or "artifact"
