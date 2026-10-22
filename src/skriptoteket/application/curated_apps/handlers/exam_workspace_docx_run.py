"""The input, the result and the per-run state of one DOCX conversion."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult,
    DocxStageTiming,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    SharedContext,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import NativeExamContentTag
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    DocumentImportOriginKind,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiJobOverageCapReached,
)
from skriptoteket.protocols.docx_conversion_progress import ConversionUpdate


@dataclass(frozen=True)
class DocxConversionOutcome:
    """The final build result and its mapping of grouped questions to items."""

    result: DocxBuildResult
    update: ConversionUpdate
    ai_limit: AiDailyLimit | None = None
    limit_code: str | None = None
    """The failure/state code of the job's first refusal: ai_daily_limit or ai_overage_cap."""


class DocxConversionPipelineProtocol(Protocol):
    """One DOCX conversion over a grouped exam; doubles inject through the constructor."""

    async def convert(
        self, *, job: DocxConversionJob, fallback_reason: str | None = ...
    ) -> DocxConversionOutcome: ...


@dataclass(frozen=True)
class DocxConversionJob:
    """Identity, source and door caller of one conversion."""

    job_id: UUID
    worker_id: str
    document_id: UUID
    filename: str
    source_sha256: str
    source_docx: bytes
    chunks: tuple[DocxChunk, ...]
    course_key: str | None
    caller: AiDoorCaller
    origin_kind: DocumentImportOriginKind


class DocxConversionRun:
    """Mutable bookkeeping of one conversion; every mutation happens under the UoW lock."""

    def __init__(self, job: DocxConversionJob, started: float) -> None:
        self.job = job
        self.started = started
        self.ai_limit: AiDailyLimit | None = None
        """The door limit of the job's first refusal; later steps take failure paths."""
        self.limit_code: str | None = None
        """The failure/state code of the first refusal: ai_daily_limit or ai_overage_cap."""
        self.state = DocxBuildState(
            job.job_id,
            job.document_id,
            job.filename,
            job.source_sha256,
            job.chunks,
            job.origin_kind,
        )
        self.manifest: ExamManifest | None = None
        self.families: tuple[QuestionFamily, ...] = ()
        self.title_anchors: frozenset[str] = frozenset()
        self.context_anchors: frozenset[str] = frozenset()
        self.contexts: tuple[SharedContext, ...] = ()
        self.own_anchors: dict[str, tuple[str, ...]] = {}
        self.key_anchors: dict[str, tuple[str, ...]] = {}
        self.kinds: dict[str, NativeExamItemKind] = {}
        # The labeler's first type per question, kept before a type-conflict resend
        # overwrites ``kinds``; the retry source persists it (TASK-SKRIPT-39-05-09 D1).
        self.label_kinds: dict[str, NativeExamItemKind] = {}
        self.resent: set[str] = set()
        self.content_tags: tuple[NativeExamContentTag, ...] = ()
        self.second_wave_dispatches = 0
        self.converting_reported = False
        self.converting_written = asyncio.Event()
        """Set once the converting phase write has completed; batches that start the converting
        phase wait for it before their first provider call."""
        self.filled: list[str] = []
        self.timings: list[DocxStageTiming] = []

    def family(self, question_id: str) -> QuestionFamily:
        return next(f for f in self.families if f.question_id == question_id)

    def note_limit(self, exc: AiDailyLimitReached | AiJobOverageCapReached) -> str:
        """Record the job's first refusal; return its failure/state code."""

        if isinstance(exc, AiJobOverageCapReached):
            code, limit = "ai_overage_cap", AiDailyLimit.POOL
        else:
            code, limit = "ai_daily_limit", exc.limit
        if self.ai_limit is None:
            self.ai_limit = limit
            self.limit_code = code
        return code

    def timed(self, stage: str, started: float) -> None:
        self.timings.append(
            DocxStageTiming(stage, started - self.started, time.monotonic() - self.started)
        )

    @property
    def pending(self) -> tuple[str, ...]:
        return tuple(f.question_id for f in self.families if f.question_id not in self.filled)
