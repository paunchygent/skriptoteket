"""Grouping-pass port for type-batched DOCX conversion (TASK-SKRIPT-39-05-04 step 1).

The grouping pass returns source references only: each question with its subparts and
answer key, each shared instruction or passage with the questions it governs and its one
owner, and the title. It writes no question text and no answers.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import ExamManifest


class ExamGroupingError(Exception):
    """Grouping failed; ``reason`` is the Swedish review reason, ``code`` is observable."""

    def __init__(self, reason: str, *, code: str, detail: str = "") -> None:
        super().__init__(reason)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class ExamGrouping:
    """The manifest, the measured usage of every grouping call, and the calls made."""

    manifest: ExamManifest
    usage: tuple[StructuredLLMUsage, ...]


class ExamGrouperProtocol(Protocol):
    """Map the exam's chunks to a manifest of source references."""

    async def group(self, *, job_id: UUID, chunks: tuple[DocxChunk, ...]) -> ExamGrouping: ...
