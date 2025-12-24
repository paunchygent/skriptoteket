from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, RunnerArtifact
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, ToolVersion


class ArtifactManagerProtocol(Protocol):
    def store_output_archive(
        self,
        *,
        run_id: UUID,
        output_archive: Iterable[bytes],
        reported_artifacts: list[RunnerArtifact],
    ) -> ArtifactsManifest: ...


class ToolRunnerProtocol(Protocol):
    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[tuple[str, bytes]],
        memory_json: bytes,
    ) -> ToolExecutionResult: ...
