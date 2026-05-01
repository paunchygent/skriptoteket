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
import html
import json
import re
from dataclasses import dataclass
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
CLASSROOM_PLANNER_PUBLIC_APP_PATH = "/public/apps/classroom.group-seating-studio"
SHARE_CREATED_DATE_PLACEHOLDER = "__SKRIPTOTEKET_SHARE_CREATED_DATE__"
SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER = "__SKRIPTOTEKET_SHARE_PDF_DOWNLOAD_PATH__"
SHARE_CREATED_DATE_CHROME_SLOT = (
    f'<span data-skriptoteket-share-created-date="owned">{SHARE_CREATED_DATE_PLACEHOLDER}</span>'
)
SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT = (
    f'href="{SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER}" data-skriptoteket-share-pdf-download="owned"'
)


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
    guest_snapshot_fingerprint: str | None = None
    client_operation_id: str | None = None
    revoke_secret_hash: str | None = None
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
    public_revoke_secret: str | None = None

    @property
    def public_path(self) -> str:
        """Build the stable anonymous public path for the share."""

        return self.artifact.public_path or build_share_public_path(
            public_token=self.public_token,
            slug=self.artifact.slug,
        )


@dataclass(frozen=True, slots=True)
class PublicGuestSharePersistenceResult:
    """Describe one atomic public guest share persistence outcome."""

    artifact: ClassroomPlannerShareArtifact | None
    superseded_previous: bool = False
    reused_client_operation: bool = False
    active_limit_exceeded: bool = False
    previous_already_superseded: bool = False


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


def hash_share_revoke_secret(secret: str) -> str:
    """Hash a browser-held public guest revoke secret for durable storage."""

    return _hash_text(secret)


def extract_share_public_token(public_path: str) -> str | None:
    """Extract the unguessable share token from a copied public path."""

    path = public_path.strip()
    if not path:
        return None
    if "://" in path:
        _, _, path = path.partition("://")
        _, _, path = path.partition("/")
        path = f"/{path}"
    parts = [part for part in path.split("/") if part]
    if len(parts) < 3 or parts[0] != "share" or parts[1] != "classroom":
        return None
    return parts[2] or None


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


def build_share_pdf_download_path(*, public_token: str) -> str:
    """Build the anonymous public PDF download path for one share token."""

    return f"/share/classroom/{public_token}/download.pdf"


def finalize_share_rendered_html(
    *,
    rendered_html: str,
    created_at: datetime,
    pdf_download_path: str,
) -> str:
    """Finalize owned share chrome slots before immutable share hashing."""

    created_date = created_at.date().isoformat()
    if rendered_html.count(SHARE_CREATED_DATE_CHROME_SLOT) != 1:
        raise ValueError("Rendered share HTML must contain exactly one owned date chrome slot.")
    if rendered_html.count(SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT) != 1:
        raise ValueError("Rendered share HTML must contain exactly one owned PDF chrome slot.")

    created_date_slot = SHARE_CREATED_DATE_CHROME_SLOT.replace(
        SHARE_CREATED_DATE_PLACEHOLDER,
        created_date,
    )
    pdf_download_href_slot = SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT.replace(
        SHARE_PDF_DOWNLOAD_PATH_PLACEHOLDER,
        html.escape(pdf_download_path, quote=True),
    )
    return rendered_html.replace(
        SHARE_CREATED_DATE_CHROME_SLOT,
        created_date_slot,
        1,
    ).replace(
        SHARE_PDF_DOWNLOAD_HREF_CHROME_SLOT,
        pdf_download_href_slot,
        1,
    )


def _hash_text(value: str) -> str:
    return _HASH_PREFIX + hashlib.sha256(value.encode("utf-8")).hexdigest()
