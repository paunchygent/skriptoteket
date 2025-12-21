from __future__ import annotations

from uuid import UUID

from pydantic import ValidationError

from skriptoteket.application.scripting.interactive_tools import (
    GetRunQuery,
    GetRunResult,
    RunArtifact,
    RunDetails,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.scripting.artifacts import ArtifactsManifest
from skriptoteket.protocols.interactive_tools import GetRunHandlerProtocol
from skriptoteket.protocols.scripting import ToolRunRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


def _artifacts_for_run(
    *,
    run_id: UUID,
    artifacts_manifest: dict[str, object],
) -> list[RunArtifact]:
    try:
        manifest = ArtifactsManifest.model_validate(artifacts_manifest)
    except ValidationError:
        return []

    return [
        RunArtifact(
            artifact_id=artifact.artifact_id,
            path=artifact.path,
            bytes=artifact.bytes,
            download_url=f"/api/v1/runs/{run_id}/artifacts/{artifact.artifact_id}",
        )
        for artifact in manifest.artifacts
    ]


class GetRunHandler(GetRunHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        runs: ToolRunRepositoryProtocol,
    ) -> None:
        self._uow = uow
        self._runs = runs

    async def handle(self, *, actor: User, query: GetRunQuery) -> GetRunResult:
        async with self._uow:
            run = await self._runs.get_by_id(run_id=query.run_id)

        if run is None or run.requested_by_user_id != actor.id:
            raise not_found("ToolRun", str(query.run_id))

        return GetRunResult(
            run=RunDetails(
                run_id=run.id,
                status=run.status,
                ui_payload=run.ui_payload,
                artifacts=_artifacts_for_run(
                    run_id=run.id, artifacts_manifest=run.artifacts_manifest
                ),
            )
        )
