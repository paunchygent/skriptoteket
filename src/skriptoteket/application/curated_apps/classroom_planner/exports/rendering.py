"""Renderer-facing contracts for classroom-planner seating poster export.

Purpose:
    Define the typed HTML/CSS bundle produced from a standalone `poster_scene`
    so application handlers can orchestrate Sir Convert-a-Lot submissions
    without embedding presentation details or zip-building logic.

Relationships:
    - Consumed by the seating export-job handlers.
    - Implemented by infrastructure poster renderers.
    - Uses `SeatingPosterScene` from the PR-0118 export contract as input.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .jobs import SeatingExportPaperSize
from .models import SeatingPosterScene


class RenderedSeatingPosterBundle(BaseModel):
    """Describe the export-owned HTML/CSS bundle for one poster job."""

    model_config = ConfigDict(frozen=True)

    html_filename: str
    html_content: str
    css_filename: str
    css_content: str
    output_filename: str


class SeatingPosterRenderRequest(BaseModel):
    """Describe the application input passed into the poster renderer."""

    model_config = ConfigDict(frozen=True)

    roster_name: str
    template_name: str
    paper_size: SeatingExportPaperSize
    scene: SeatingPosterScene
