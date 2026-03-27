"""Protocols for the Conversion Hub curated app.

Purpose:
  Provide typed persistence seams for Conversion Hub's locally owned job ledger
  so the application layer can own job identity, status refresh, and artifact
  authorization without coupling to infrastructure details.

Relationships:
  - Used by `application.curated_apps.handlers.conversion_hub_jobs`.
  - Implemented by `infrastructure.repositories.conversion_hub_jobs`.
"""

from __future__ import annotations

from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.conversion_hub import ConversionHubJob


class ConversionHubJobRepositoryProtocol(Protocol):
    """Persist local Conversion Hub jobs."""

    async def create(self, *, job: ConversionHubJob) -> ConversionHubJob: ...

    async def get_by_id(self, *, job_id: UUID) -> ConversionHubJob | None: ...

    async def update(self, *, job: ConversionHubJob) -> ConversionHubJob: ...
