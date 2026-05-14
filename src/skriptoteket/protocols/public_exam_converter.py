"""Protocols for the public Exam Converter runtime.

Purpose:
  Define application-facing seams for transient public job state and HuleEdu
  public grant minting without coupling the runtime to storage or HTTP clients.

Relationships:
  - Implemented by Conversion Hub infrastructure adapters.
  - Used by `application.curated_apps.handlers.public_exam_converter_jobs`.
  - Complements `protocols.sir_convert_a_lot_v2` for the upstream conversion hop.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Protocol

from skriptoteket.application.curated_apps.public_exam_converter import (
    PublicExamConverterSubmittedJob,
    PublicExamConverterTarget,
)
from skriptoteket.protocols.sir_convert_a_lot_v2 import (
    SirConvertArtifactV2,
    SirConvertJobV2,
)


@dataclass(frozen=True, slots=True)
class PublicExamConverterGrantRequest:
    """Server-side request for a HuleEdu public conversion grant."""

    upload_digest: str
    aggregate_upload_bytes: int
    upload_mime_types: tuple[str, ...]
    allowed_targets: tuple[PublicExamConverterTarget, ...]
    correlation_id: str


@dataclass(frozen=True, slots=True)
class PublicExamConverterGrant:
    """Opaque HuleEdu-signed public grant retained only server-side."""

    token: str
    artifact_ttl_seconds: int
    expires_at: datetime


class PublicExamConverterGrantAuthorityProtocol(Protocol):
    async def mint_conversion_grant(
        self,
        *,
        request: PublicExamConverterGrantRequest,
    ) -> PublicExamConverterGrant: ...


class PublicExamConverterJobStoreProtocol(Protocol):
    async def create(
        self, *, job: PublicExamConverterSubmittedJob
    ) -> PublicExamConverterSubmittedJob: ...

    async def get(
        self, *, public_job_id: str, now: datetime
    ) -> PublicExamConverterSubmittedJob | None: ...

    async def update(
        self, *, job: PublicExamConverterSubmittedJob
    ) -> PublicExamConverterSubmittedJob: ...

    async def count_active(self, *, now: datetime) -> int: ...


@dataclass(frozen=True, slots=True)
class PublicExamConverterSirConvertSubmitRequest:
    filename: str
    content_type: str
    file_bytes: bytes
    job_spec: dict[str, object]
    idempotency_key: str
    wait_seconds: int
    correlation_id: str
    public_conversion_grant: str
    graded_result_pdf_filename: str | None = None
    graded_result_pdf_bytes: bytes | None = None


@dataclass(frozen=True, slots=True)
class PublicExamConverterSirConvertSubmittedJob:
    job_id: str
    status: str
    idempotent_replay: bool
    manifest_artifact_read_lease_token: str


class PublicExamConverterSirConvertProtocol(Protocol):
    async def submit_public_exam_converter_job(
        self,
        *,
        request: PublicExamConverterSirConvertSubmitRequest,
    ) -> PublicExamConverterSirConvertSubmittedJob: ...

    async def get_public_exam_converter_job(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        correlation_id: str,
    ) -> SirConvertJobV2: ...

    async def get_public_exam_converter_result(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        correlation_id: str,
    ) -> dict[str, object]: ...

    async def get_public_exam_converter_artifact_manifest(
        self,
        job_id: str,
        *,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> dict[str, object]: ...

    async def download_public_exam_converter_artifact(
        self,
        job_id: str,
        *,
        artifact_key: str,
        public_conversion_grant: str,
        public_artifact_read_lease: str,
        correlation_id: str,
    ) -> SirConvertArtifactV2: ...
