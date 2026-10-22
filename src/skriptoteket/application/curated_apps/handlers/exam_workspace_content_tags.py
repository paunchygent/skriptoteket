"""Saved-head content-tag suggestion requests and the existing queue's worker lane."""

from __future__ import annotations

from uuid import UUID

from pydantic import BaseModel, ConfigDict

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
    finish_enrichment_job,
)
from skriptoteket.application.curated_apps.exam_content_tagging import (
    ExamContentTagSuggester,
)
from skriptoteket.application.curated_apps.exam_workspace_content_suggestions import (
    ContentSuggestionsResponse,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    ExamContentItem,
    NativeExamContentTag,
    load_exam_content_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import User
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorCaller,
    AiJobOverageCapReached,
    ai_limit_note,
    door_caller_for,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceDocumentHandlerProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.identity import UserRepositoryProtocol
from skriptoteket.protocols.item_type_labeler import ContentTagClassificationRequest, LabelingItem
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_DEFAULT_FAILURE_MESSAGE = "Innehållsförslaget kunde inte hämtas. Försök igen senare."


class ExamCourseContentResponse(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    course_key: str
    items: tuple[ExamContentItem, ...]


def course_content(course_key: str) -> ExamCourseContentResponse:
    if not any(course.key == course_key for course in load_exam_course_catalog().courses):
        raise not_found("course", course_key)
    return ExamCourseContentResponse(
        course_key=course_key, items=load_exam_content_catalog()[course_key]
    )


class ContentSuggestionsPayload(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    suggestions: tuple[NativeExamContentTag, ...]


def content_response(job: ExamAnswerKeyEnrichmentJob) -> ContentSuggestionsResponse:
    assert job.workspace_lineage_id is not None
    assert job.workspace_document_revision is not None
    assert job.workspace_course_key is not None
    payload = (
        ContentSuggestionsPayload.model_validate(job.workspace_suggestions_json)
        if job.workspace_suggestions_json is not None
        else None
    )
    if job.ai_limit is not None:
        message: str | None = ai_limit_note(job.ai_limit)
    else:
        message = _DEFAULT_FAILURE_MESSAGE if job.last_error else None
    return ContentSuggestionsResponse(
        job_id=job.id,
        lineage_id=job.workspace_lineage_id,
        document_revision=job.workspace_document_revision,
        course_key=job.workspace_course_key,
        state=job.status,
        ai_limit=job.ai_limit,
        suggestions=payload.suggestions if payload else (),
        message=message,
    )


class RequestExamContentSuggestionsHandler:
    def __init__(
        self,
        *,
        reader: GetExamWorkspaceDocumentHandlerProtocol,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
        id_generator: IdGeneratorProtocol,
    ) -> None:
        self._reader, self._jobs, self._uow = reader, jobs, uow
        self._clock, self._ids = clock, id_generator

    async def handle(self, *, actor: User, lineage_id: UUID) -> ContentSuggestionsResponse:
        saved = (await self._reader.handle(actor=actor, lineage_id=lineage_id)).saved_document
        if saved.header.course is None:
            raise validation_error("Välj och spara en kurs innan du föreslår innehåll.")
        now = self._clock.now()
        job = ExamAnswerKeyEnrichmentJob(
            id=self._ids.new_uuid(),
            source_kind=ExamAnswerKeySourceKind.CONTENT_TAGS,
            owner_user_id=actor.id,
            status=ExamAnswerKeyEnrichmentJobStatus.QUEUED,
            input_filename=saved.title[:255],
            workspace_lineage_id=lineage_id,
            workspace_document_revision=saved.revision,
            workspace_course_key=saved.header.course.key,
            workspace_request_json=saved.model_dump(mode="json"),
            available_at=now,
            created_at=now,
            updated_at=now,
        )
        async with self._uow:
            job = await self._jobs.create(job=job)
        return content_response(job)


class GetExamContentSuggestionsHandler:
    def __init__(self, *, jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol) -> None:
        self._jobs = jobs

    async def handle(
        self, *, actor: User, lineage_id: UUID, job_id: UUID
    ) -> ContentSuggestionsResponse:
        job = await self._jobs.get_by_id(job_id=job_id)
        if (
            job is None
            or job.owner_user_id != actor.id
            or job.source_kind is not ExamAnswerKeySourceKind.CONTENT_TAGS
            or job.workspace_lineage_id != lineage_id
        ):
            raise not_found("content_suggestion", str(job_id))
        return content_response(job)


def saved_content_request(
    document: NativeExamDocument, job_id: UUID, caller: AiDoorCaller
) -> ContentTagClassificationRequest:
    assert document.header.course is not None
    items = []
    for item in document.items:
        parent = document.parent_of(item.item_id)
        text = "\n".join(
            (
                body_plain_text(document.instructions),
                body_plain_text(parent.instruction) if parent else "",
                *item.plain_text_lines(),
                *(body_plain_text(choice.body) for choice in item.choices),
                *(body_plain_text(entry.body) for entry in item.match_left),
                *(body_plain_text(entry.body) for entry in item.match_right),
            )
        )
        items.append(LabelingItem(item_id=item.item_id, source_text=text))
    return ContentTagClassificationRequest(
        job_id=job_id,
        items=tuple(items),
        content_items=load_exam_content_catalog()[document.header.course.key],
        caller=caller,
    )


class ProcessExamContentSuggestionsHandler:
    def __init__(
        self,
        *,
        classifier: ExamContentTagSuggester,
        jobs: ExamAnswerKeyEnrichmentJobRepositoryProtocol,
        users: UserRepositoryProtocol,
        uow: UnitOfWorkProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._classifier, self._jobs, self._uow, self._clock = classifier, jobs, uow, clock
        self._users = users

    async def handle(self, *, job: ExamAnswerKeyEnrichmentJob) -> ExamAnswerKeyEnrichmentJob:
        try:
            document = NativeExamDocument.model_validate(job.workspace_request_json)
            if (
                document.document_id != job.workspace_lineage_id
                or document.revision != job.workspace_document_revision
                or document.header.course is None
                or document.header.course.key != job.workspace_course_key
            ):
                raise ValueError("Content job does not match its saved document")
            owner = await self._users.get_by_id(job.owner_user_id)
            if owner is None:
                return await self.fail(job=job, last_error="owner_missing")
            tags = await self._classifier.suggest(
                request=saved_content_request(document, job.id, door_caller_for(user=owner)),
                fail_open=False,
            )
            payload = ContentSuggestionsPayload(suggestions=tags)
            job = job.model_copy(
                update={"workspace_suggestions_json": payload.model_dump(mode="json")}
            )
        except AiDailyLimitReached as exc:
            return await self.fail(job=job, last_error="ai_daily_limit", ai_limit=exc.limit)
        except AiJobOverageCapReached:
            return await self.fail(job=job, last_error="ai_overage_cap", ai_limit=AiDailyLimit.POOL)
        except Exception:
            return await self.fail(job=job, last_error="content_suggestions_failed")
        async with self._uow:
            return await self._jobs.update(
                job=finish_enrichment_job(
                    job=job,
                    status=ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED,
                    now=self._clock.now(),
                ),
                expected_worker_id=job.locked_by,
            )

    async def fail(
        self,
        *,
        job: ExamAnswerKeyEnrichmentJob,
        last_error: str,
        ai_limit: AiDailyLimit | None = None,
    ) -> ExamAnswerKeyEnrichmentJob:
        if ai_limit is not None:
            job = job.model_copy(update={"ai_limit": ai_limit})
        async with self._uow:
            return await self._jobs.update(
                job=finish_enrichment_job(
                    job=job,
                    status=ExamAnswerKeyEnrichmentJobStatus.FAILED,
                    now=self._clock.now(),
                    last_error=last_error,
                ),
                expected_worker_id=job.locked_by,
            )
