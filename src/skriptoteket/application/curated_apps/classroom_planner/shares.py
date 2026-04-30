"""Share artifact contracts for Klassrumskartan published links.

Purpose:
    Define the immutable share artifact shape used by authenticated and public
    Klassrumskartan share-link flows without coupling application handlers to
    SQLAlchemy, FastAPI, or future route rendering.

Relationships:
    - Persisted through `ClassroomPlannerShareArtifactRepositoryProtocol`.
    - Created by share handlers under the classroom-planner application layer.
    - Reuses `PlanDraftKind` from the planner domain so shares stay tied to the
      grouping/seating task boundary.
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.classroom_planner.models import PlanDraftKind

type JsonScalar = str | int | float | bool | None
type JsonValue = JsonScalar | list["JsonValue"] | dict[str, "JsonValue"]
type JsonObject = dict[str, JsonValue]

_HASH_PREFIX = "sha256:"
_SLUG_PART_PATTERN = re.compile(r"[^a-z0-9]+")


class ClassroomPlannerShareArtifactSource(StrEnum):
    """Enumerate the authority source for one immutable share artifact."""

    AUTHENTICATED = "authenticated"
    PUBLIC_GUEST = "public_guest"


class ClassroomPlannerShareArtifact(BaseModel):
    """Represent one persisted immutable Klassrumskartan share artifact."""

    model_config = ConfigDict(frozen=True)

    id: UUID
    token_hash: str
    source: ClassroomPlannerShareArtifactSource
    draft_kind: PlanDraftKind
    owner_user_id: UUID | None = None
    draft_id: UUID | None = None
    roster_id: UUID | None = None
    template_id: UUID | None = None
    source_revision: int | None = Field(default=None, ge=0)
    title: str
    slug: str
    public_path: str | None = None
    preview_description: str | None = None
    renderer_version: str
    presentation_schema_version: str
    presentation_hash: str
    content_hash: str
    presentation_payload: JsonObject | None = None
    rendered_html: str
    rendered_css: str
    created_at: datetime
    updated_at: datetime
    revoked_at: datetime | None = None
    expires_at: datetime | None = None

    @property
    def is_revoked(self) -> bool:
        """Return whether the share was explicitly revoked."""

        return self.revoked_at is not None


class ClassroomPlannerShareArtifactCreateResult(BaseModel):
    """Return a newly persisted share plus the creation-time public token."""

    model_config = ConfigDict(frozen=True)

    artifact: ClassroomPlannerShareArtifact
    public_token: str

    @property
    def public_path(self) -> str:
        """Build the stable anonymous public path for the share."""

        return self.artifact.public_path or build_share_public_path(
            public_token=self.public_token,
            slug=self.artifact.slug,
        )


class RenderedClassroomPlannerShare(BaseModel):
    """Carry one canonical server-rendered share artifact before persistence."""

    model_config = ConfigDict(frozen=True)

    title: str
    preview_description: str
    renderer_version: str
    presentation_schema_version: str
    presentation_payload: JsonObject
    rendered_html: str
    rendered_css: str


def hash_share_token(token: str) -> str:
    """Hash a public share token for durable storage."""

    return _hash_text(token)


def build_share_content_hash(*, rendered_html: str, rendered_css: str) -> str:
    """Hash rendered share output as one immutable content fingerprint."""

    return _hash_text(f"{rendered_html}\0{rendered_css}")


def build_share_presentation_hash(payload: JsonObject | None) -> str:
    """Hash canonical presentation payload or an explicit empty provenance."""

    if payload is None:
        return _hash_text("null")
    canonical_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    )
    return _hash_text(canonical_payload)


def build_share_slug(title: str) -> str:
    """Build a cosmetic URL slug from the share title."""

    normalized = title.strip().casefold()
    slug = _SLUG_PART_PATTERN.sub("-", normalized).strip("-")
    return slug or "klassrumskarta"


def build_share_public_path(*, public_token: str, slug: str) -> str:
    """Build the anonymous public path that teachers can copy later."""

    return f"/share/classroom/{public_token}/{slug}"


def _hash_text(value: str) -> str:
    return _HASH_PREFIX + hashlib.sha256(value.encode("utf-8")).hexdigest()
