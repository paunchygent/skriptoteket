"""Boundary models for exam content-tag suggestion jobs."""

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    NativeExamContentTag,
)
from skriptoteket.domain.llm_door import AiDailyLimit


class ContentSuggestionsResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    job_id: UUID
    lineage_id: UUID
    document_revision: int
    course_key: str
    state: ExamAnswerKeyEnrichmentJobStatus
    ai_limit: AiDailyLimit | None = None
    suggestions: tuple[NativeExamContentTag, ...] = ()
    message: str | None = None
