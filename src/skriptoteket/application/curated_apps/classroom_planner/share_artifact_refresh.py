"""Refresh helpers for persisted Klassrumskartan share artifacts.

Purpose:
    Re-render legacy seating share artifacts from their stored presentation
    payload when a seating-only renderer correction changes persisted HTML/CSS.

Relationships:
    - Used by `handlers.share_artifacts` during preview backfill.
    - Keeps token, source, and lifecycle semantics unchanged.
    - Delegates rendering through `ClassroomPlannerShareRendererProtocol`.
"""

from __future__ import annotations

from datetime import datetime

from skriptoteket.application.curated_apps.classroom_planner.exports import (
    PreparedSeatingExportContract,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    build_share_content_hash,
    build_share_pdf_download_path,
    build_share_presentation_hash,
    extract_share_public_token,
    finalize_share_rendered_html,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.classroom_planner_shares import (
    ClassroomPlannerShareRendererProtocol,
)


def refresh_seating_share_artifact_if_needed(
    *,
    artifact: ClassroomPlannerShareArtifact,
    renderer: ClassroomPlannerShareRendererProtocol,
    current_seating_renderer_version: str,
    refreshed_at: datetime,
) -> ClassroomPlannerShareArtifact:
    """Return a seating artifact re-rendered with the current seating renderer."""

    if (
        artifact.draft_kind is not PlanDraftKind.SEATING
        or artifact.renderer_version == current_seating_renderer_version
    ):
        return artifact

    if artifact.presentation_payload is None:
        raise validation_error("Seating share artifact requires presentation payload refresh.")
    public_token = extract_share_public_token(artifact.public_path or "")
    if public_token is None:
        raise validation_error("Seating share artifact refresh requires a public path token.")

    prepared_export = PreparedSeatingExportContract.model_validate(artifact.presentation_payload)
    rendered = renderer.render_seating(prepared_export=prepared_export)
    rendered_html = finalize_share_rendered_html(
        rendered_html=rendered.rendered_html,
        created_at=artifact.created_at,
        pdf_download_path=build_share_pdf_download_path(public_token=public_token),
    )
    return artifact.model_copy(
        update={
            "title": rendered.title,
            "preview_description": rendered.preview_description,
            "renderer_version": rendered.renderer_version,
            "presentation_schema_version": rendered.presentation_schema_version,
            "presentation_payload": rendered.presentation_payload,
            "presentation_hash": build_share_presentation_hash(rendered.presentation_payload),
            "content_hash": build_share_content_hash(
                rendered_html=rendered_html,
                rendered_css=rendered.rendered_css,
            ),
            "rendered_html": rendered_html,
            "rendered_css": rendered.rendered_css,
            "updated_at": refreshed_at,
        }
    )
