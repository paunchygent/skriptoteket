"""Web DTOs for authenticated Klassrumskartan share links.

Purpose:
    Expose typed API contracts for creating, listing, and revoking immutable
    classroom-planner share artifacts without leaking persistence models or
    public-token hashes.

Relationships:
    - Used by grouping, seating, and common share API routers.
    - Serializes application share artifacts from
      `skriptoteket.application.curated_apps.classroom_planner.shares`.
"""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
    ClassroomPlannerShareArtifactCreateResult,
    ClassroomPlannerShareArtifactSource,
)
from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind
from skriptoteket.web.spa_metadata import absolute_public_url


class CreateClassroomPlannerShareRequest(BaseModel):
    """Deserialize an authenticated share creation request."""

    expected_revision: int = Field(ge=0)


class ClassroomPlannerShareArtifactDto(BaseModel):
    """Serialize persisted share metadata without exposing token hashes."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    source: ClassroomPlannerShareArtifactSource
    draft_kind: PlanDraftKind
    draft_id: UUID | None
    roster_id: UUID | None
    template_id: UUID | None
    source_revision: int | None
    title: str
    slug: str
    public_path: str | None
    public_url: str | None
    preview_description: str | None
    renderer_version: str
    presentation_schema_version: str
    presentation_hash: str
    content_hash: str
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None
    expires_at: datetime | None


class CreatedClassroomPlannerShareDto(BaseModel):
    """Serialize a newly created share including the one-time public URL."""

    model_config = ConfigDict(frozen=True)

    artifact: ClassroomPlannerShareArtifactDto
    public_path: str
    public_url: str


def serialize_share_artifact(
    artifact: ClassroomPlannerShareArtifact,
    *,
    public_app_base_url: str | None = None,
) -> ClassroomPlannerShareArtifactDto:
    """Map an application share artifact to API metadata."""

    public_url = (
        absolute_public_url(public_base_url=public_app_base_url, path=artifact.public_path)
        if public_app_base_url and artifact.public_path
        else None
    )
    return ClassroomPlannerShareArtifactDto(
        id=artifact.id,
        source=artifact.source,
        draft_kind=artifact.draft_kind,
        draft_id=artifact.draft_id,
        roster_id=artifact.roster_id,
        template_id=artifact.template_id,
        source_revision=artifact.source_revision,
        title=artifact.title,
        slug=artifact.slug,
        public_path=artifact.public_path,
        public_url=public_url,
        preview_description=artifact.preview_description,
        renderer_version=artifact.renderer_version,
        presentation_schema_version=artifact.presentation_schema_version,
        presentation_hash=artifact.presentation_hash,
        content_hash=artifact.content_hash,
        created_at=artifact.created_at,
        updated_at=artifact.updated_at,
        revoked_at=artifact.revoked_at,
        expires_at=artifact.expires_at,
    )


def serialize_created_share(
    result: ClassroomPlannerShareArtifactCreateResult,
    *,
    public_app_base_url: str,
) -> CreatedClassroomPlannerShareDto:
    """Map a created share result to API metadata plus a one-time public URL."""

    public_path = result.public_path
    public_url = absolute_public_url(public_base_url=public_app_base_url, path=public_path)
    return CreatedClassroomPlannerShareDto(
        artifact=serialize_share_artifact(
            result.artifact,
            public_app_base_url=public_app_base_url,
        ),
        public_path=public_path,
        public_url=public_url,
    )
