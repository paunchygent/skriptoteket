"""Exam workspace application DTOs (ST-SKRIPT-39-04 walking skeleton)."""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from skriptoteket.application.curated_apps.exam_workspace_export_blockers import (
    NativeDocumentWithExportBlockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import ExamCourse
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import ExamListOrdering
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    InlineChoiceMinOptions,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKeySuggestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    IMPORTABLE_ITEM_KINDS,
    NativeExamItemKind,
)


class ExamWorkspaceDocumentSummary(BaseModel):
    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    version: int = Field(ge=1)
    vault_file_id: UUID
    name: str
    saved_at: datetime
    course_key: str | None
    title: str


class ExamWorkspaceConversionUnit(BaseModel):
    """Items conversion last wrote for one question or question-less review item.

    ``converting`` items are placeholders that only the unit's later batch may change;
    ``ready`` items are converted and editable.
    """

    model_config = ConfigDict(frozen=True)

    unit_id: str
    question: bool
    state: Literal["converting", "ready"]
    item_ids: tuple[str, ...]


class ExamWorkspaceConversionStatus(BaseModel):
    """Owner-visible status of one background DOCX import.

    ``document_revision`` is the latest revision conversion saved, absent until the
    first batch is ready; ``units`` lets the editor merge each new revision into
    unsaved teacher edits.
    """

    model_config = ConfigDict(frozen=True)

    job_id: UUID
    lineage_id: UUID
    state: Literal["queued", "running", "succeeded", "failed"]
    error_message: str | None
    document_revision: int | None
    questions_total: int
    questions_done: int
    units: tuple[ExamWorkspaceConversionUnit, ...]
    summary: ExamWorkspaceDocumentSummary | None


class ExamWorkspaceDocumentResponse(NativeDocumentWithExportBlockers):
    """The teacher's working copy and the durable exam file it stands on.

    ``document`` includes the selected undo step; ``saved_document`` is the exam
    file at ``summary.version``, the baseline for Spara and dirty state.
    ``conversion`` is read under the same lock as the document, so its units name exactly
    the placeholders this revision still holds; it is None for a lineage no import created.
    ``export_blockers`` is the export gate's verdict on ``document``, so the workspace shows
    what the gate will refuse without a rule of its own.
    """

    model_config = ConfigDict(frozen=True)

    saved_document: NativeExamDocument
    summary: ExamWorkspaceDocumentSummary
    history_cursor: UUID
    notes: tuple[str, ...] = ()
    conversion: ExamWorkspaceConversionStatus | None


class ExamWorkspaceDocumentGroup(BaseModel):
    model_config = ConfigDict(frozen=True)

    course_key: str | None
    course_name: str
    documents: tuple[ExamWorkspaceDocumentSummary, ...]


class ExamWorkspaceDocumentListResponse(BaseModel):
    """The actor's workspace documents, one head version per lineage."""

    model_config = ConfigDict(frozen=True)

    ordering: ExamListOrdering
    documents: tuple[ExamWorkspaceDocumentSummary, ...]
    groups: tuple[ExamWorkspaceDocumentGroup, ...]


class ExamCourseCatalogResponse(BaseModel):
    """The committed course catalog, loaded once per page and searched in the browser."""

    model_config = ConfigDict(frozen=True)

    generated_at: str
    courses: tuple[ExamCourse, ...] = ()
    registered_course_keys: tuple[str, ...] = ()


class SaveExamWorkspaceDocumentRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    expected_revision: int = Field(ge=1)
    document: NativeExamDocument
    position_step_id: UUID
    """The retained history snapshot the editor stands on; the saved copy is kept at it."""


class ExamWorkspaceEnrichmentState(StrEnum):
    """Teacher-facing state of one answer-key suggestion job."""

    NOT_ELIGIBLE = "not_eligible"
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class RequestExamWorkspaceAnswerKeySuggestionsRequest(BaseModel):
    """Editor-sent content for one suggestion request (TASK-SKRIPT-39-04-07).

    ``document`` is the exam exactly as the editor shows it, saved or not.
    With ``item_id`` the request covers that one question, with or without
    a key; without it, it covers every keyed-kind question without a key.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument
    item_id: str | None = None


class ExamWorkspaceAnswerKeySuggestionItem(BaseModel):
    """One AI suggestion that arrived for one question."""

    model_config = ConfigDict(frozen=True)

    item_id: str
    suggestion: NativeAnswerKeySuggestion


class ExamWorkspaceAnswerKeySuggestionsResponse(BaseModel):
    """Status of one suggestion job, plus its suggestions once finished."""

    model_config = ConfigDict(frozen=True)

    job_id: UUID | None = None
    lineage_id: UUID
    state: ExamWorkspaceEnrichmentState
    message: str | None = None
    suggestions: tuple[ExamWorkspaceAnswerKeySuggestionItem, ...] = ()


class RetryExamWorkspaceItemRequest(BaseModel):
    """Editor-sent content for one single-question reconversion (TASK-SKRIPT-39-05-09 D1).

    ``document`` is the exam exactly as the editor shows it; the saved head revision is the
    authority for the question's original source, so the draft's own copy of the item is
    never read as source. ``kind`` is the type the teacher keeps or chooses.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    document: NativeExamDocument
    item_id: str
    kind: NativeExamItemKind

    @field_validator("kind")
    @classmethod
    def _importable_kind(cls, value: NativeExamItemKind) -> NativeExamItemKind:
        if value not in IMPORTABLE_ITEM_KINDS:
            raise ValueError("a retry never produces ordering questions")
        return value


class ExamWorkspaceItemRetryResponse(BaseModel):
    """The one item a retry replaces its question with; everything else stays put."""

    model_config = ConfigDict(frozen=True)

    lineage_id: UUID
    item: NativeExamItem


class ExamWorkspaceExportTarget(StrEnum):
    QTI = "qti"
    PDF = "pdf"
    PDF_FACIT = "pdf_facit"
    DOCX = "docx"
    EXAMNET_PDF = "examnet_pdf"


class ExamWorkspaceExportFile(BaseModel):
    model_config = ConfigDict(frozen=True)

    filename: str
    media_type: str
    content: bytes


class ExamWorkspaceExportChecklistCriterion(BaseModel):
    """One Fritext criterion's text and points, which Exam.net replaces with a bare row."""

    model_config = ConfigDict(frozen=True)

    text: str
    points: int


class ExamWorkspaceExportChecklistFreeTextCriteria(BaseModel):
    """One Fritext question whose criteria import as unlabelled 1-point rows (Q13)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["free_text_criteria"]
    question_number: str
    question_text: str
    points: int | float
    criteria: tuple[ExamWorkspaceExportChecklistCriterion, ...]


class ExamWorkspaceExportChecklistAllOrNothing(BaseModel):
    """One shared-instruction subquestion Exam.net gives 1 point instead of its own (Q16)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["all_or_nothing"]
    question_number: str
    question_text: str
    points: int | float


class ExamWorkspaceExportChecklistRoundedGaps(BaseModel):
    """One Lucktext whose rounded per-gap value leaves part of its points unused (Q17)."""

    model_config = ConfigDict(frozen=True)

    kind: Literal["rounded_gaps"]
    question_number: str
    question_text: str
    points: int | float
    gap_points: int | float


ExamWorkspaceExportChecklistEntry = Annotated[
    ExamWorkspaceExportChecklistFreeTextCriteria
    | ExamWorkspaceExportChecklistAllOrNothing
    | ExamWorkspaceExportChecklistRoundedGaps,
    Field(discriminator="kind"),
]


class ExamWorkspaceExportChecklistResponse(BaseModel):
    """What an Exam.net import of this document's QTI package loses (Q15-Q17).

    ``inline_choice_min_options`` publishes the export rule's dropdown minimum, so the
    workspace readiness mirror reads it from this contract instead of restating it.
    """

    model_config = ConfigDict(frozen=True)

    entries: tuple[ExamWorkspaceExportChecklistEntry, ...]
    inline_choice_min_options: InlineChoiceMinOptions


class ExamWorkspacePrintPreviewResponse(BaseModel):
    """The saved student print copy as preview page images, or why it cannot be rendered (W5).

    ``pages`` holds one PNG data URL per printed page, in print order, so the
    Förhandsgranska panel can show the exam page by page. ``question_pages`` maps each
    question's item id to the 0-based index of the page it first appears on, so the
    panel can scroll to the selected question. ``status`` is ``blocked`` when the
    document cannot be rendered at all (for example a declared picture without stored
    payload); the student copy prints drafts, so the export blocker gate never runs here.
    """

    model_config = ConfigDict(frozen=True)

    revision: int
    status: Literal["ready", "blocked"]
    pages: list[str]
    question_pages: dict[str, int]
    message: str | None
