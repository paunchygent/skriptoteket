"""Content enrichment uses saved state and keeps results on its own queue row."""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.exam_content_tagging import (
    ExamContentTagSuggester,
)
from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceDocumentResponse
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    GetExamContentSuggestionsHandler,
    ProcessExamContentSuggestionsHandler,
    RequestExamContentSuggestionsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.exam_content_tags import (
    ExamContentItem,
    NativeExamContentTag,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import ExamCourseChoice
from skriptoteket.domain.errors import DomainError
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_container import (
    ExamWorkspaceContainerCodec,
)
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.exam_answer_key import ExamAnswerKeyEnrichmentJobRepositoryProtocol
from skriptoteket.protocols.exam_workspace import GetExamWorkspaceDocumentHandlerProtocol
from skriptoteket.protocols.id_generator import IdGeneratorProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.enrichment_routing_test_support import make_actor
from tests.unit.application.curated_apps.handlers.workspace_suggestion_handler_support import (
    NOW,
    suggestion_document,
    suggestion_item,
)

pytestmark = pytest.mark.unit
_CONTENT = (ExamContentItem(id="SVESVE02:grammatik", text="Språkets uppbyggnad"),)


class _Setup:
    def __init__(self) -> None:
        self.actor = make_actor()
        self.lineage = uuid4()
        self.saved = suggestion_document(
            self.lineage, suggestion_item(item_id="item_001", sequence=1, stem="Sparad fråga")
        )
        self.saved = self.saved.model_copy(
            update={
                "header": self.saved.header.model_copy(
                    update={
                        "course": ExamCourseChoice(key="SVESVE02", name="Svenska 2"),
                    }
                ),
            }
        )
        self.reader = AsyncMock(spec=GetExamWorkspaceDocumentHandlerProtocol)
        response = Mock(spec=ExamWorkspaceDocumentResponse)
        response.saved_document = self.saved
        response.document = self.saved.model_copy(
            update={
                "revision": 99,
                "header": self.saved.header.model_copy(
                    update={
                        "course": ExamCourseChoice(key="SVESVE03", name="Svenska 3"),
                    }
                ),
            }
        )
        self.reader.handle.return_value = response
        self.jobs = AsyncMock(spec=ExamAnswerKeyEnrichmentJobRepositoryProtocol)
        self.jobs.create.side_effect = lambda *, job: job
        self.jobs.update.side_effect = lambda *, job, expected_worker_id: job
        self.uow = AsyncMock(spec=UnitOfWorkProtocol)
        self.clock = Mock(spec=ClockProtocol)
        self.clock.now.return_value = NOW
        ids = Mock(spec=IdGeneratorProtocol)
        ids.new_uuid.return_value = uuid4()
        self.request = RequestExamContentSuggestionsHandler(
            reader=self.reader,
            jobs=self.jobs,
            uow=self.uow,
            clock=self.clock,
            id_generator=ids,
        )

    async def enqueue(self):
        await self.request.handle(actor=self.actor, lineage_id=self.lineage)
        return self.jobs.create.call_args.kwargs["job"]


@pytest.mark.asyncio
async def test_request_snapshots_saved_head_not_unsaved_course_or_revision() -> None:
    setup = _Setup()
    job = await setup.enqueue()
    setup.reader.handle.assert_awaited_once_with(actor=setup.actor, lineage_id=setup.lineage)
    assert job.source_kind is ExamAnswerKeySourceKind.CONTENT_TAGS
    assert job.workspace_course_key == "SVESVE02"
    assert job.workspace_document_revision == 3
    assert job.workspace_request_json == setup.saved.model_dump(mode="json")
    assert job.workspace_suggestions_json is None


@pytest.mark.asyncio
async def test_unsaved_course_does_not_make_courseless_saved_exam_eligible() -> None:
    setup = _Setup()
    setup.reader.handle.return_value.saved_document = setup.saved.model_copy(
        update={
            "header": setup.saved.header.model_copy(update={"course": None}),
        }
    )
    with pytest.raises(DomainError):
        await setup.request.handle(actor=setup.actor, lineage_id=setup.lineage)
    setup.jobs.create.assert_not_awaited()


@pytest.mark.asyncio
async def test_worker_stores_tag_citations_on_job_row_without_saving_document(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    setup = _Setup()
    job = (await setup.enqueue()).model_copy(
        update={
            "status": ExamAnswerKeyEnrichmentJobStatus.RUNNING,
            "locked_by": "content-worker",
        }
    )
    monkeypatch.setattr(
        "skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags."
        "load_exam_content_catalog",
        lambda: {"SVESVE02": _CONTENT},
    )
    classifier = Mock(spec=ExamContentTagSuggester)
    tag = NativeExamContentTag(
        id=_CONTENT[0].id,
        text=_CONTENT[0].text,
        origin="suggested",
        question_ids=("item_001",),
    )
    classifier.suggest = AsyncMock(return_value=(tag,))
    users = UserRepositoryStub()
    users.user = setup.actor
    worker = ProcessExamContentSuggestionsHandler(
        classifier=classifier,
        jobs=setup.jobs,
        users=users,
        uow=setup.uow,
        clock=setup.clock,
    )
    finished = await worker.handle(job=job)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.SUCCEEDED
    assert finished.workspace_suggestions_json == {"suggestions": [tag.model_dump(mode="json")]}
    assert finished.workspace_request_json == job.workspace_request_json
    assert setup.saved.header.tags == ()
    request = classifier.suggest.call_args.kwargs["request"]
    assert request.job_id == job.id
    assert request.content_items == _CONTENT
    assert request.caller.user_id == setup.actor.id
    assert request.items[0].item_id == "item_001"
    assert "Sparad fråga" in request.items[0].source_text
    assert "eleverna" in request.items[0].source_text
    setup.jobs.update.assert_awaited_once_with(job=finished, expected_worker_id="content-worker")


@pytest.mark.asyncio
@pytest.mark.parametrize("binding", ["lineage", "revision", "course"])
async def test_worker_rejects_snapshot_bound_to_another_exam_version_or_course(
    binding: str,
) -> None:
    setup = _Setup()
    fields = {
        "lineage": {"workspace_lineage_id": uuid4()},
        "revision": {"workspace_document_revision": 7},
        "course": {"workspace_course_key": "SVESVE03"},
    }
    job = (await setup.enqueue()).model_copy(update=fields[binding])
    classifier = Mock(spec=ExamContentTagSuggester)
    classifier.suggest = AsyncMock()
    users = UserRepositoryStub()
    users.user = setup.actor
    worker = ProcessExamContentSuggestionsHandler(
        classifier=classifier,
        jobs=setup.jobs,
        users=users,
        uow=setup.uow,
        clock=setup.clock,
    )
    finished = await worker.handle(job=job)
    assert finished.status is ExamAnswerKeyEnrichmentJobStatus.FAILED
    assert finished.workspace_suggestions_json is None
    classifier.suggest.assert_not_awaited()


@pytest.mark.asyncio
@pytest.mark.parametrize("binding", ["owner", "lineage", "source"])
async def test_status_does_not_disclose_other_owners_or_queue_lane_results(binding: str) -> None:
    setup = _Setup()
    fields = {
        "owner": {"owner_user_id": uuid4()},
        "lineage": {"workspace_lineage_id": uuid4()},
        "source": {"source_kind": ExamAnswerKeySourceKind.WORKSPACE},
    }
    job = (await setup.enqueue()).model_copy(update=fields[binding])
    setup.jobs.get_by_id.return_value = job
    handler = GetExamContentSuggestionsHandler(jobs=setup.jobs)
    with pytest.raises(DomainError):
        await handler.handle(actor=setup.actor, lineage_id=setup.lineage, job_id=job.id)


@pytest.mark.parametrize("new_course", [None, ExamCourseChoice(key="SVESVE03", name="Svenska 3")])
def test_container_preserves_tag_text_origin_and_citations_until_course_changes(new_course) -> None:
    setup = _Setup()
    tag = NativeExamContentTag(
        id=_CONTENT[0].id,
        text=_CONTENT[0].text,
        origin="teacher",
        question_ids=("item_001",),
    )
    document = setup.saved.model_copy(
        update={
            "header": setup.saved.header.model_copy(update={"tags": (tag,)}),
        }
    )
    codec = ExamWorkspaceContainerCodec()
    content = ExamWorkspaceContainerContent(document=document, assets_by_id={}, notes=())
    reopened = codec.parse(content=codec.build(content=content)).document
    assert reopened.header.tags == (tag,)
    changed = reopened.model_dump(mode="json")
    changed["header"]["course"] = new_course.model_dump(mode="json") if new_course else None
    changed_document = type(document).model_validate(changed)
    assert changed_document.header.tags == ()
