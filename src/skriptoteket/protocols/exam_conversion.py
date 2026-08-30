"""Exam Converter in-process conversion protocols.

Purpose:
    Keep the in-process dxe -> Exam.net bundle lane protocol-first so the
    conversion producer, deterministic QTI packaging, WeasyPrint rendering,
    and local artifact storage can evolve independently of FastAPI and
    concrete filesystem code.

Relationships:
    Used by ``application.curated_apps.exam_conversion_producers`` and
    ``application.curated_apps.handlers.exam_converter_conversions``;
    implemented under ``infrastructure.curated_apps.apps.conversion_hub``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.exam_conversion import (
    ExamConversionNamedArtifact,
    ExamConversionStoredArtifact,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_contracts import (
    DigiExamExamNetPdfDocument,
)
from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiPackagePlan,
)

if TYPE_CHECKING:
    from skriptoteket.application.curated_apps.handlers.conversion_hub_jobs import (
        ConversionHubUpload,
    )


class ExamNetQtiPackageWriterProtocol(Protocol):
    """Materialize deterministic QTI package and report bytes from domain plans."""

    def build_package_bytes(self, plan: ExamNetQtiPackagePlan) -> bytes: ...

    def build_validation_report_bytes(
        self,
        *,
        plan: ExamNetQtiPackagePlan,
        package_filename: str,
        package_bytes: bytes | None,
    ) -> bytes: ...

    def build_bundle_bytes(self, *, entries: tuple[tuple[str, bytes], ...]) -> bytes: ...


class ExamNetPdfRendererProtocol(Protocol):
    """Render one successful Exam.net PDF document plan into PDF bytes."""

    def render_pdf(self, *, document: DigiExamExamNetPdfDocument) -> bytes: ...


class InProcessExamConverterProtocol(Protocol):
    """Produce one Exam.net bundle artifact from an uploaded `.dxe` export."""

    async def convert(
        self,
        *,
        job_id: UUID,
        upload: "ConversionHubUpload",
        overlay_bytes: bytes | None,
        proposal_overlay_bytes: bytes | None = None,
        proposal_provider_profile_id: str | None = None,
        proposal_model: str | None = None,
        teacher_answer_key_item_ids: frozenset[str] = frozenset(),
        correlation_id: str | None,
        overlay_key_provenance: DigiExamAnswerKeyProvenance = (
            DigiExamAnswerKeyProvenance.MANUAL_TEACHER_KEY
        ),
    ) -> ExamConversionStoredArtifact: ...


class ExamConversionArtifactStoreProtocol(Protocol):
    """Store and read server-owned in-process Exam Converter artifacts."""

    def store_artifact(
        self,
        *,
        job_id: UUID,
        artifact: ExamConversionStoredArtifact,
    ) -> None: ...

    def read_artifact(self, *, job_id: UUID) -> ExamConversionStoredArtifact: ...

    def read_named_artifact(
        self,
        *,
        job_id: UUID,
        artifact_key: str,
    ) -> ExamConversionNamedArtifact: ...
