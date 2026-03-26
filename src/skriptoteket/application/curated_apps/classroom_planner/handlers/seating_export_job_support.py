"""Support helpers for classroom-planner seating export jobs.

Purpose:
    Keep the public export-job result mapping separate from the orchestration
    handlers so seating export routes can share one small, stable translation
    helper regardless of whether the artifact was produced as PDF or XLSX.

Relationships:
    - Used by `seating_export_jobs.py`.
    - Depends on application export-job models and Vault repositories only.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    SeatingExportJob,
    SeatingExportJobResult,
    SeatingExportVaultArtifact,
)
from skriptoteket.protocols.vault import VaultFileRepositoryProtocol


async def build_job_result(
    *,
    job: SeatingExportJob,
    vault_files: VaultFileRepositoryProtocol | None,
) -> SeatingExportJobResult:
    """Build the public job result from one persisted export job."""

    vault_artifact = None
    if job.vault_file_id is not None and vault_files is not None:
        vault_file = await vault_files.get_by_id(file_id=job.vault_file_id)
        if vault_file is not None:
            vault_artifact = SeatingExportVaultArtifact(
                file_id=vault_file.id,
                name=vault_file.name,
                bytes=vault_file.bytes,
                created_at=vault_file.created_at,
            )
    download_url = (
        f"/api/v1/apps/classroom.group-seating-studio/exports/jobs/{job.id}/download"
        if vault_artifact is not None
        else None
    )
    return SeatingExportJobResult(
        job_id=job.id,
        draft_id=job.draft_id,
        export_kind=job.export_kind,
        layout_id=job.layout_id,
        paper_size=job.paper_size,
        status=job.status,
        created_at=job.created_at,
        download_url=download_url,
        vault_artifact=vault_artifact,
        error=job.error_message,
    )
