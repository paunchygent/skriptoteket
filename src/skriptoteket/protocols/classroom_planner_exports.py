"""Protocols for classroom-planner export jobs and rendering.

Purpose:
    Provide typed seams for the dedicated seating and grouping export-job
    repositories plus the renderers that later turn prepared export models into
    teacher-facing artifacts.

Relationships:
    - Used by application handlers under
      `application.curated_apps.classroom_planner.handlers`.
    - Implemented by repository and renderer modules under `infrastructure`.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    grouping_jobs,
    grouping_pdf_view_model,
    grouping_xlsx_view_model,
    rendering,
    seating_xlsx_view_model,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportJob,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.rendering import (
    RenderedSeatingPosterBundle,
    SeatingPosterRenderRequest,
)


class SeatingExportJobRepositoryProtocol(Protocol):
    """Persist dedicated seating export jobs."""

    async def create(self, *, job: SeatingExportJob) -> SeatingExportJob: ...

    async def get_by_id(self, *, job_id: UUID) -> SeatingExportJob | None: ...

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> SeatingExportJob | None: ...

    async def get_latest_in_flight_for_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
    ) -> SeatingExportJob | None: ...

    async def get_latest_downloadable_for_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
    ) -> SeatingExportJob | None: ...

    async def update(self, *, job: SeatingExportJob) -> SeatingExportJob: ...


class GroupingExportJobRepositoryProtocol(Protocol):
    """Persist dedicated grouping export jobs."""

    async def create(
        self,
        *,
        job: grouping_jobs.GroupingExportJob,
    ) -> grouping_jobs.GroupingExportJob: ...

    async def get_by_id(self, *, job_id: UUID) -> grouping_jobs.GroupingExportJob | None: ...

    async def get_by_upstream_job_id(
        self,
        *,
        upstream_job_id: str,
    ) -> grouping_jobs.GroupingExportJob | None: ...

    async def get_latest_in_flight_for_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
    ) -> grouping_jobs.GroupingExportJob | None: ...

    async def get_latest_downloadable_for_draft(
        self,
        *,
        owner_user_id: UUID,
        draft_id: UUID,
    ) -> grouping_jobs.GroupingExportJob | None: ...

    async def update(
        self,
        *,
        job: grouping_jobs.GroupingExportJob,
    ) -> grouping_jobs.GroupingExportJob: ...


class SeatingPosterRendererProtocol(Protocol):
    """Render a standalone poster scene into export-owned HTML/CSS."""

    def render(self, *, request: SeatingPosterRenderRequest) -> RenderedSeatingPosterBundle: ...


class SeatingPdfRendererProtocol(Protocol):
    """Render one seating poster HTML/CSS bundle into final PDF bytes."""

    def render(
        self,
        *,
        bundle: rendering.RenderedSeatingPosterBundle,
    ) -> bytes: ...


class SeatingXlsxRendererProtocol(Protocol):
    """Render a teacher-facing seating workbook into XLSX bytes."""

    def render(
        self,
        *,
        view_model: seating_xlsx_view_model.SeatingXlsxWorkbookViewModel,
    ) -> bytes: ...


class GroupingXlsxRendererProtocol(Protocol):
    """Render a teacher-facing grouping workbook into XLSX bytes."""

    def render(
        self,
        *,
        view_model: grouping_xlsx_view_model.GroupingXlsxWorkbookViewModel,
    ) -> bytes: ...


class GroupingPdfRendererProtocol(Protocol):
    """Render a grouping PDF handout into final PDF bytes."""

    def render(
        self,
        *,
        view_model: grouping_pdf_view_model.GroupingPdfViewModel,
    ) -> bytes: ...
