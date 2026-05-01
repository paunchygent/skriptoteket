"""Application contracts for public guest Klassrumskartan share links.

Purpose:
    Define the browser-owned public guest share request and response contracts
    used by the ADR-0084 public helper boundary.

Relationships:
    - Reuses `ClassroomPlannerGuestSnapshotPayload` for canonical snapshot input.
    - Returned by public guest share handlers and serialized by public API routes.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.application.curated_apps.classroom_planner.guest_upgrade_contracts import (
    ClassroomPlannerGuestSnapshotPayload,
)
from skriptoteket.application.curated_apps.classroom_planner.shares import (
    ClassroomPlannerShareArtifact,
)


class PublicGuestShareRequest(BaseModel):
    """Describe one public guest share creation request from a browser snapshot."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    snapshot: ClassroomPlannerGuestSnapshotPayload
    expected_revision: int = Field(ge=0)
    client_operation_id: str = Field(min_length=16, max_length=128)
    revoke_secret: str = Field(min_length=32, max_length=256)
    previous_public_path: str | None = Field(default=None, max_length=512)
    previous_revoke_secret: str | None = Field(default=None, min_length=32, max_length=256)


class PublicGuestShareResult(BaseModel):
    """Return a public guest share plus browser-held lifecycle metadata."""

    model_config = ConfigDict(frozen=True)

    artifact: ClassroomPlannerShareArtifact
    public_path: str
    public_revoke_secret: str
    superseded_previous: bool
    reused_client_operation: bool = False


class PublicGuestShareRevokeRequest(BaseModel):
    """Describe a browser-owned public guest share revoke request."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    public_path: str = Field(min_length=1, max_length=512)
    revoke_secret: str = Field(min_length=32, max_length=256)


class PublicGuestShareRevokeResult(BaseModel):
    """Return the public guest share revoked by browser-held metadata."""

    model_config = ConfigDict(frozen=True)

    artifact: ClassroomPlannerShareArtifact
    public_path: str
