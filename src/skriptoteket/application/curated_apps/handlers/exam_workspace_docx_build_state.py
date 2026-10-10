"""Accepted source, retry payload and measured usage for one DOCX build."""

from dataclasses import dataclass, field
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    DocxBuildResult,
    SourceText,
    answer_key_chunks,
    assemble_build_result,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamItem


@dataclass
class DocxBuildState:
    """Freeze accepted items while keeping answer-key evidence reusable."""

    document_id: UUID
    filename: str
    source_sha256: str
    chunks: tuple[DocxChunk, ...]
    reason: str = "AI-tolkningen kunde inte valideras mot källan efter tre försök."
    accepted: list[tuple[NativeExamItem, tuple[str, ...]]] = field(default_factory=list)
    title: SourceText | None = None
    instructions: tuple[SourceText, ...] = ()
    claimed: set[str] = field(default_factory=set)
    failures: tuple[str, ...] = ()
    pending: tuple[DocxChunk, ...] = field(init=False)
    key_anchors: set[str] = field(init=False)
    input_tokens: int | None = None
    output_tokens: int | None = None
    input_complete: bool = True
    output_complete: bool = True

    def __post_init__(self) -> None:
        self.pending = self.chunks
        self.key_anchors = {chunk.anchor for chunk in answer_key_chunks(self.chunks)}

    def record_usage(self, usage: StructuredLLMUsage) -> None:
        """Accumulate measured usage, retaining unknown totals as unknown."""
        if usage.prompt_tokens is not None and usage.prompt_tokens >= 0:
            self.input_tokens = (self.input_tokens or 0) + usage.prompt_tokens
        else:
            self.input_complete = False
        if usage.completion_tokens is not None and usage.completion_tokens >= 0:
            self.output_tokens = (self.output_tokens or 0) + usage.completion_tokens
        else:
            self.output_complete = False

    def advance_pending(self, errors: list[str]) -> None:
        """Retain unclaimed content and facit until only facit remains."""
        self.pending = tuple(chunk for chunk in self.chunks if chunk.anchor not in self.claimed)
        if self.accepted and {chunk.anchor for chunk in self.pending} <= self.key_anchors:
            self.pending = ()
        self.failures = tuple(errors) or ("Källstycken saknar validerade frågor eller metadata.",)

    def result(self) -> DocxBuildResult:
        """Assemble frozen items, source metadata and review fallbacks."""
        return assemble_build_result(
            document_id=self.document_id,
            filename=self.filename,
            source_sha256=self.source_sha256,
            chunks=self.chunks,
            accepted=tuple(self.accepted),
            title=self.title,
            instructions=self.instructions,
            reason=self.reason,
            input_tokens=self.input_tokens if self.input_complete else None,
            output_tokens=self.output_tokens if self.output_complete else None,
        )
