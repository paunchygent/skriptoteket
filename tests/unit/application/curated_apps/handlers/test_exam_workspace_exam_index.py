"""Exam list ordering must follow teacher preferences, not vault or key order."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.exam_workspace import SaveExamWorkspaceDocumentRequest
from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListExamWorkspaceDocumentsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import SavedExam
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamHeader,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import ExamCourses, User, UserProfile
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol
from tests.unit.application.curated_apps.handlers.exam_workspace_conversion_support import choice
from tests.unit.application.curated_apps.handlers.test_exam_workspace_documents import _actor, _Env

_NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _exam(*, owner: User, course: str | None, title: str, age: int) -> SavedExam:
    return SavedExam(
        owner_user_id=owner.id,
        lineage_id=uuid4(),
        course_key=course,
        title=title,
        saved_at=_NOW - timedelta(days=age),
        head_vault_file_id=uuid4(),
        name=f"{title}.provdokument.zip",
        version=3,
    )


@pytest.mark.asyncio
async def test_registered_courses_keep_profile_order_then_official_names_then_no_course() -> None:
    actor = _actor()
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    uow = AsyncMock(spec=UnitOfWorkProtocol)
    # No-course is newest overall; registered order deliberately reverses course names.
    exams = [
        _exam(owner=actor, course=None, title="Unassigned", age=0),
        _exam(owner=actor, course="MATMAT01b", title="Math", age=1),
        _exam(owner=actor, course="SVESVE01", title="Svenska latest", age=2),
        _exam(owner=actor, course="ENGENG05", title="English", age=3),
        _exam(owner=actor, course="SVEN2000X", title="Svenska 2", age=4),
        _exam(owner=actor, course="SVESVE01", title="Svenska older", age=5),
    ]
    index.list_for_owner.return_value = exams
    profiles.get_by_user_id.return_value = UserProfile(
        user_id=actor.id,
        exam_courses=ExamCourses(course_keys=["SVEN2000X", "SVESVE01"]),
        exam_list_ordering="course",
        created_at=_NOW,
        updated_at=_NOW,
    )
    result = await ListExamWorkspaceDocumentsHandler(
        index=index, profiles=profiles, uow=uow
    ).handle(actor=actor)

    assert result.ordering == "course"
    assert [group.course_key for group in result.groups] == [
        "SVEN2000X",
        "SVESVE01",
        "ENGENG05",
        "MATMAT01b",
        None,
    ]
    catalog = {course.key: course for course in load_exam_course_catalog().courses}
    assert [group.course_name for group in result.groups] == [
        catalog[key].name for key in ("SVEN2000X", "SVESVE01", "ENGENG05", "MATMAT01b")
    ] + ["Utan kurs"]
    assert [exam.title for exam in result.groups[1].documents] == [
        "Svenska latest",
        "Svenska older",
    ]
    assert [exam.title for exam in result.documents] == [
        "Svenska 2",
        "Svenska latest",
        "Svenska older",
        "English",
        "Math",
        "Unassigned",
    ]
    # Every summary must expose joined head fields without loading document containers.
    by_lineage = {exam.lineage_id: exam for exam in exams}
    for summary in result.documents:
        saved = by_lineage[summary.lineage_id]
        assert summary.vault_file_id == saved.head_vault_file_id
        assert summary.name == saved.name
        assert summary.version == saved.version
        assert summary.saved_at == saved.saved_at
        assert summary.course_key == saved.course_key
        assert summary.title == saved.title
    index.list_for_owner.assert_awaited_once_with(owner_user_id=actor.id)
    profiles.get_by_user_id.assert_awaited_once_with(user_id=actor.id)


@pytest.mark.asyncio
async def test_flat_order_uses_saved_profile_preference_not_registered_group_order() -> None:
    actor = _actor()
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    exams = [
        _exam(owner=actor, course=None, title="Newest no course", age=0),
        _exam(owner=actor, course="SVESVE01", title="Middle", age=1),
        _exam(owner=actor, course="SVEN2000X", title="Oldest registered first", age=9),
    ]
    expected_lineages = tuple(exam.lineage_id for exam in exams)
    index.list_for_owner.return_value = [exams[2], exams[0], exams[1]]
    profiles.get_by_user_id.return_value = UserProfile(
        user_id=actor.id,
        exam_courses=ExamCourses(course_keys=["SVEN2000X", "SVESVE01"]),
        exam_list_ordering="newest",
        created_at=_NOW,
        updated_at=_NOW,
    )
    result = await ListExamWorkspaceDocumentsHandler(
        index=index, profiles=profiles, uow=AsyncMock(spec=UnitOfWorkProtocol)
    ).handle(actor=actor)
    assert result.ordering == "newest"
    assert tuple(exam.lineage_id for exam in result.documents) == expected_lineages
    assert not result.groups


@pytest.mark.asyncio
async def test_unregistered_course_names_override_course_code_and_save_date_order() -> None:
    actor = _actor()
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.list_for_owner.return_value = [
        _exam(owner=actor, course="SVASVA01", title="SVA newer", age=0),
        _exam(owner=actor, course="SVESVE02", title="Svenska older", age=2),
    ]
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = UserProfile(
        user_id=actor.id, exam_list_ordering="course", created_at=_NOW, updated_at=_NOW
    )
    result = await ListExamWorkspaceDocumentsHandler(
        index=index, profiles=profiles, uow=AsyncMock(spec=UnitOfWorkProtocol)
    ).handle(actor=actor)
    assert [(group.course_key, group.course_name) for group in result.groups] == [
        ("SVESVE02", "Svenska 2"),
        ("SVASVA01", "Svenska som andraspråk 1"),
    ]


@pytest.mark.asyncio
async def test_first_save_and_changed_course_replace_one_index_row_with_current_metadata() -> None:
    env, actor = _Env(), _actor()
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="First title",
        header=NativeExamHeader(course=ExamCourseChoice(key="SVESVE01", name="Svenska 1")),
        items=(choice("body:0001", "A question"),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    file = await env.store.save(
        actor=actor,
        file_id=uuid4(),
        name="Filename differs from title.provdokument.zip",
        content=env.codec.build(content=ExamWorkspaceContainerContent(document=document)),
        lineage_id=document.document_id,
        version=1,
    )
    indexed = await env.index.get(owner_user_id=actor.id, lineage_id=document.document_id)
    assert indexed is not None
    assert indexed.title == "First title"
    assert indexed.course_key == "SVESVE01"
    assert indexed.head_vault_file_id == file.id
    assert indexed.saved_at == file.document_saved_at
    changed = document.model_copy(
        update={
            "revision": 2,
            "title": "Changed title",
            "header": NativeExamHeader(course=ExamCourseChoice(key="ENGENG05", name="Engelska 5")),
        }
    )
    response = await env.save_handler.handle(
        actor=actor,
        lineage_id=document.document_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=1, document=changed),
    )
    listed = await env.list_handler.handle(actor=actor)
    assert len(env.index.entries) == 1
    assert len(listed.documents) == 1
    assert listed.documents[0] == response.summary
    assert response.summary.title == "Changed title"
    assert response.summary.course_key == "ENGENG05"
    assert response.summary.vault_file_id == file.id
    assert response.summary.version == 2
    assert response.summary.name == "Filename differs from title.provdokument.zip"
    # Clearing a course must clear the persisted metadata, not retain the previous key.
    cleared = changed.model_copy(update={"revision": 3, "header": NativeExamHeader()})
    response = await env.save_handler.handle(
        actor=actor,
        lineage_id=document.document_id,
        request=SaveExamWorkspaceDocumentRequest(expected_revision=2, document=cleared),
    )
    assert response.summary.course_key is None
    listed = await env.list_handler.handle(actor=actor)
    assert listed.groups[-1].course_name == "Utan kurs"
    assert listed.documents == (response.summary,)


@pytest.mark.asyncio
async def test_unknown_course_cannot_create_an_unlistable_saved_exam() -> None:
    env, actor = _Env(), _actor()
    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="A forged course selection",
        header=NativeExamHeader(course=ExamCourseChoice(key="missing:course", name="Invented")),
        items=(choice("body:0001", "A question"),),
        origin=NativeExamDocumentOrigin(kind="created"),
    )
    with pytest.raises(DomainError) as error:
        await env.store.save(
            actor=actor,
            file_id=uuid4(),
            name="Prov.provdokument.zip",
            content=env.codec.build(content=ExamWorkspaceContainerContent(document=document)),
            lineage_id=document.document_id,
            version=1,
        )
    assert error.value.code is ErrorCode.VALIDATION_ERROR
    assert not env.vault_files.files
    assert not env.index.entries
    assert not env.vault_storage.stored


@pytest.mark.asyncio
async def test_empty_index_returns_no_invented_empty_course_groups() -> None:
    actor = _actor()
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.list_for_owner.return_value = []
    profiles = AsyncMock(spec=ProfileRepositoryProtocol)
    profiles.get_by_user_id.return_value = UserProfile(
        user_id=actor.id,
        exam_courses=ExamCourses(course_keys=["SVESVE01"]),
        exam_list_ordering="course",
        created_at=_NOW,
        updated_at=_NOW,
    )
    result = await ListExamWorkspaceDocumentsHandler(
        index=index, profiles=profiles, uow=AsyncMock(spec=UnitOfWorkProtocol)
    ).handle(actor=actor)
    assert result.documents == ()
    assert result.groups == ()
