"""Protocols for classroom-planner seating export jobs and rendering.

Purpose:
    Provide typed seams for the dedicated seating export-job repository and the
    renderer that turns a prepared poster scene into export-owned HTML/CSS.

Relationships:
    - Used by application handlers under
      `application.curated_apps.classroom_planner.handlers`.
    - Implemented by repository and renderer modules under `infrastructure`.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.classroom_planner.exports.jobs import (
    SeatingExportJob,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.rendering import (
    RenderedSeatingPosterBundle,
    SeatingPosterRenderRequest,
)
from skriptoteket.application.curated_apps.classroom_planner.exports.webhook_bindings import (
    SeatingExportWebhookBinding,
)


class SeatingExportJobRepositoryProtocol(Protocol):
    """Persist dedicated seating export jobs."""

    async def create(self, *, job: SeatingExportJob) -> SeatingExportJob: ...

    async def get_by_id(self, *, job_id: UUID) -> SeatingExportJob | None: ...

    async def get_by_upstream_job_id(self, *, upstream_job_id: str) -> SeatingExportJob | None: ...

    async def update(self, *, job: SeatingExportJob) -> SeatingExportJob: ...


class SeatingExportWebhookBindingRepositoryProtocol(Protocol):
    """Persist the single shared seating-export webhook binding."""

    async def get_shared_for_update(self) -> SeatingExportWebhookBinding: ...

    async def update_shared(
        self,
        *,
        binding: SeatingExportWebhookBinding,
    ) -> SeatingExportWebhookBinding: ...


class SeatingPosterRendererProtocol(Protocol):
    """Render a standalone poster scene into export-owned HTML/CSS."""

    def render(self, *, request: SeatingPosterRenderRequest) -> RenderedSeatingPosterBundle: ...
