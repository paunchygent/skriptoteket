"""PostgreSQL repository for locally owned Conversion Hub jobs.

Purpose:
  Map the `conversion_hub_jobs` table to typed application models so the
  Conversion Hub bounded context can own job identity and authorization without
  leaking persistence details into handlers or routes.

Relationships:
  - Implements `ConversionHubJobRepositoryProtocol`.
  - Uses `ConversionHubJobModel` from the infrastructure DB model package.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from skriptoteket.application.curated_apps.conversion_hub import (
    ConversionHubJob,
    ConversionHubPdfLayoutV2,
)
from skriptoteket.infrastructure.db.models.conversion_hub_job import ConversionHubJobModel
from skriptoteket.protocols.conversion_hub import ConversionHubJobRepositoryProtocol


class PostgreSQLConversionHubJobRepository(ConversionHubJobRepositoryProtocol):
    """Persist Conversion Hub jobs in PostgreSQL."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def _to_model(self, job: ConversionHubJob) -> ConversionHubJobModel:
        pdf_layout = job.pdf_layout
        return ConversionHubJobModel(
            id=job.id,
            owner_user_id=job.owner_user_id,
            input_filename=job.input_filename,
            source_format=job.source_format.value,
            output_format=job.output_format.value,
            pdf_paper_size=pdf_layout.paper_size.value if pdf_layout is not None else None,
            pdf_orientation=pdf_layout.orientation.value if pdf_layout is not None else None,
            pdf_margins_mm=pdf_layout.margins_mm if pdf_layout is not None else None,
            upstream_job_id=job.upstream_job_id,
            status=job.status.value,
            correlation_id=job.correlation_id,
            error_message=job.error_message,
            created_at=job.created_at,
            updated_at=job.updated_at,
        )

    def _to_job(self, model: ConversionHubJobModel) -> ConversionHubJob:
        pdf_layout = None
        if (
            model.pdf_paper_size is not None
            and model.pdf_orientation is not None
            and model.pdf_margins_mm is not None
        ):
            pdf_layout = ConversionHubPdfLayoutV2(
                paper_size=model.pdf_paper_size,
                orientation=model.pdf_orientation,
                margins_mm=model.pdf_margins_mm,
            )
        return ConversionHubJob(
            id=model.id,
            owner_user_id=model.owner_user_id,
            input_filename=model.input_filename,
            source_format=model.source_format,
            output_format=model.output_format,
            pdf_layout=pdf_layout,
            upstream_job_id=model.upstream_job_id,
            status=model.status,
            correlation_id=model.correlation_id,
            error_message=model.error_message,
            created_at=model.created_at,
            updated_at=model.updated_at,
        )

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob:
        model = self._to_model(job)
        self._session.add(model)
        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None:
        model = await self._session.get(ConversionHubJobModel, job_id)
        return self._to_job(model) if model is not None else None

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> ConversionHubJob | None:
        result = await self._session.execute(
            select(ConversionHubJobModel).where(
                ConversionHubJobModel.upstream_job_id == upstream_job_id
            )
        )
        model = result.scalar_one_or_none()
        return self._to_job(model) if model is not None else None

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob:
        model = await self._session.get(ConversionHubJobModel, job.id)
        if model is None:
            return job

        pdf_layout = job.pdf_layout
        model.input_filename = job.input_filename
        model.source_format = job.source_format.value
        model.output_format = job.output_format.value
        model.pdf_paper_size = pdf_layout.paper_size.value if pdf_layout is not None else None
        model.pdf_orientation = pdf_layout.orientation.value if pdf_layout is not None else None
        model.pdf_margins_mm = pdf_layout.margins_mm if pdf_layout is not None else None
        model.upstream_job_id = job.upstream_job_id
        model.status = job.status.value
        model.correlation_id = job.correlation_id
        model.error_message = job.error_message

        await self._session.flush()
        await self._session.refresh(model)
        return self._to_job(model)
