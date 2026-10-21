"""Dispatch tests for the machine answer-key enrichment processor.

Purpose:
    Prove that every remaining enrichment source kind runs on its own lane for
    both a claimed job and an expired worker-lease job, that an unrecognised kind is
    rejected instead of falling through to a default lane, and that the job
    contract refuses a missing or retired (`dxe`) source kind.

Relationships:
    - Exercises `application.curated_apps.handlers.exam_answer_key_enrichment_jobs`
      against in-memory protocol fakes and mocked lane handlers.
"""

from __future__ import annotations

from datetime import timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.application.curated_apps.exam_answer_key_enrichment import (
    ExamAnswerKeyEnrichmentJob,
    ExamAnswerKeyEnrichmentJobStatus,
    ExamAnswerKeySourceKind,
)
from skriptoteket.application.curated_apps.handlers import exam_answer_key_enrichment_jobs
from skriptoteket.application.curated_apps.handlers.exam_answer_key_enrichment_jobs import (
    ProcessExamAnswerKeyEnrichmentJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_content_tags import (
    ProcessExamContentSuggestionsHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_digiexam_jobs import (
    ProcessExamWorkspaceDigiExamJobHandler,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_jobs import (
    ProcessExamWorkspaceDocxJobHandler,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMUsage,
)
from tests.fixtures.application_fixtures import FakeUow
from tests.fixtures.profile_app_continuation_support import UserRepositoryStub
from tests.unit.application.curated_apps.handlers.answer_key_enrichment_test_support import (
    _NOW,
    FixedClock,
    InMemoryEnrichmentJobRepository,
    StubProvider,
    _profile,
)

pytestmark = pytest.mark.unit

_ALL_KINDS = tuple(ExamAnswerKeySourceKind)


class _Lanes:
    """The four lane collaborators of the dispatcher, each a mock."""

    def __init__(self) -> None:
        self.workspace = AsyncMock()
        self.content_tags = AsyncMock(spec=ProcessExamContentSuggestionsHandler)
        self.digiexam = AsyncMock(spec=ProcessExamWorkspaceDigiExamJobHandler)
        self.docx = AsyncMock(spec=ProcessExamWorkspaceDocxJobHandler)

    def by_kind(self, kind: ExamAnswerKeySourceKind) -> AsyncMock:
        return {
            ExamAnswerKeySourceKind.WORKSPACE: self.workspace,
            ExamAnswerKeySourceKind.CONTENT_TAGS: self.content_tags,
            ExamAnswerKeySourceKind.DIGIEXAM_IMPORT: self.digiexam,
            ExamAnswerKeySourceKind.DOCX_IMPORT: self.docx,
        }[kind]

    def called_kinds(self) -> set[ExamAnswerKeySourceKind]:
        return {kind for kind in _ALL_KINDS if self.by_kind(kind).mock_calls}


def _handler(
    *, lanes: _Lanes, monkeypatch: pytest.MonkeyPatch
) -> tuple[ProcessExamAnswerKeyEnrichmentJobHandler, InMemoryEnrichmentJobRepository]:
    monkeypatch.setattr(
        exam_answer_key_enrichment_jobs,
        "ExamAnswerKeyEnrichmentWorkspaceLane",
        lambda **_: lanes.workspace,
    )
    jobs = InMemoryEnrichmentJobRepository()
    handler = ProcessExamAnswerKeyEnrichmentJobHandler(
        enrichment_jobs=jobs,
        provider=StubProvider(content={}, usage=StructuredLLMUsage(total_tokens=1)),
        users=UserRepositoryStub(),
        answer_key_profile=_profile(),
        uow=FakeUow(),
        clock=FixedClock(_NOW),
        docx_handler=lanes.docx,
        digiexam_handler=lanes.digiexam,
        content_tags_handler=lanes.content_tags,
    )
    return handler, jobs


def _running_job(kind: ExamAnswerKeySourceKind) -> ExamAnswerKeyEnrichmentJob:
    return ExamAnswerKeyEnrichmentJob(
        id=uuid4(),
        source_kind=kind,
        owner_user_id=uuid4(),
        status=ExamAnswerKeyEnrichmentJobStatus.RUNNING,
        input_filename="exam",
        source_dxe=b"dxe" if kind is ExamAnswerKeySourceKind.DIGIEXAM_IMPORT else None,
        source_docx=b"docx" if kind is ExamAnswerKeySourceKind.DOCX_IMPORT else None,
        workspace_lineage_id=uuid4(),
        workspace_document_revision=1,
        locked_by="worker-1",
        locked_until=_NOW - timedelta(seconds=1),
        available_at=_NOW,
        created_at=_NOW,
        updated_at=_NOW,
    )


@pytest.mark.parametrize("kind", _ALL_KINDS)
async def test_claimed_job_runs_only_on_its_own_lane(
    kind: ExamAnswerKeySourceKind, monkeypatch: pytest.MonkeyPatch
) -> None:
    lanes = _Lanes()
    handler, _ = _handler(lanes=lanes, monkeypatch=monkeypatch)
    job = _running_job(kind)

    await handler.handle(job=job)

    assert lanes.called_kinds() == {kind}
    lanes.by_kind(kind).handle.assert_awaited_once_with(job=job)


@pytest.mark.parametrize("kind", _ALL_KINDS)
async def test_expired_job_fails_closed_only_on_its_own_lane(
    kind: ExamAnswerKeySourceKind, monkeypatch: pytest.MonkeyPatch
) -> None:
    lanes = _Lanes()
    handler, jobs = _handler(lanes=lanes, monkeypatch=monkeypatch)
    job = _running_job(kind)
    await jobs.create(job=job)

    await handler.fail_next_expired(worker_id="reaper", now=_NOW, lease_ttl=timedelta(minutes=15))

    assert lanes.called_kinds() == {kind}
    (call,) = lanes.by_kind(kind).mock_calls
    assert call.kwargs["job"].id == job.id


async def test_unrecognised_source_kind_is_rejected_without_reaching_any_lane(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    lanes = _Lanes()
    handler, jobs = _handler(lanes=lanes, monkeypatch=monkeypatch)
    retired = _running_job(ExamAnswerKeySourceKind.WORKSPACE).model_copy(
        update={"source_kind": "dxe"}
    )

    with pytest.raises(ValueError, match="Unsupported enrichment source kind"):
        await handler.handle(job=retired)

    await jobs.create(job=retired)
    with pytest.raises(ValueError, match="Unsupported enrichment source kind"):
        await handler.fail_next_expired(
            worker_id="reaper", now=_NOW, lease_ttl=timedelta(minutes=15)
        )
    assert lanes.called_kinds() == set()


def _job_fields() -> dict[str, object]:
    return {
        "id": uuid4(),
        "owner_user_id": uuid4(),
        "status": ExamAnswerKeyEnrichmentJobStatus.QUEUED,
        "input_filename": "exam",
        "workspace_lineage_id": uuid4(),
        "workspace_document_revision": 1,
        "workspace_request_json": {},
        "available_at": _NOW,
        "created_at": _NOW,
        "updated_at": _NOW,
    }


def test_job_without_source_kind_fails_validation() -> None:
    with pytest.raises(ValidationError, match="source_kind"):
        ExamAnswerKeyEnrichmentJob.model_validate(_job_fields())


def test_job_with_retired_dxe_source_kind_fails_validation() -> None:
    with pytest.raises(ValidationError, match="source_kind"):
        ExamAnswerKeyEnrichmentJob.model_validate(_job_fields() | {"source_kind": "dxe"})


def test_job_with_a_remaining_source_kind_validates() -> None:
    job = ExamAnswerKeyEnrichmentJob.model_validate(
        _job_fields() | {"source_kind": ExamAnswerKeySourceKind.WORKSPACE.value}
    )

    assert job.source_kind is ExamAnswerKeySourceKind.WORKSPACE


def test_job_no_longer_carries_a_conversion_job_binding() -> None:
    assert "conversion_job_id" not in ExamAnswerKeyEnrichmentJob.model_fields
