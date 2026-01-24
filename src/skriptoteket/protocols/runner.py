from __future__ import annotations

from collections.abc import Iterable
from typing import Protocol
from uuid import UUID

from pydantic import JsonValue

from skriptoteket.domain.scripting.artifacts import ArtifactsManifest, RunnerArtifact
from skriptoteket.domain.scripting.execution import ToolExecutionResult
from skriptoteket.domain.scripting.models import RunContext, ToolVersion
from skriptoteket.domain.scripting.run_inputs import ResolvedInputFile


class ArtifactManagerProtocol(Protocol):
    def store_output_archive(
        self,
        *,
        run_id: UUID,
        output_archive: Iterable[bytes],
        reported_artifacts: list[RunnerArtifact],
    ) -> ArtifactsManifest: ...

    def read_artifact(
        self,
        *,
        run_id: UUID,
        artifact_path: str,
    ) -> bytes: ...


class ToolRunnerProtocol(Protocol):
    async def execute(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
        input_files: list[ResolvedInputFile],
        input_values: dict[str, JsonValue],
        memory_json: bytes,
        action_payload: dict[str, JsonValue] | None,
    ) -> ToolExecutionResult: ...


class ToolRunnerAdoptionProtocol(Protocol):
    async def try_adopt(
        self,
        *,
        run_id: UUID,
        version: ToolVersion,
        context: RunContext,
    ) -> ToolExecutionResult | None: ...
