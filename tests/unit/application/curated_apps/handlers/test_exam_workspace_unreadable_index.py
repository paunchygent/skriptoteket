"""Unreadable saved exams list only what the index flags as unreadable."""

from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_saved_index import (
    ListUnreadableExamWorkspaceDocumentsHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_index import SavedExam
from skriptoteket.domain.identity.models import AuthProvider, Role, User
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol

_NOW = datetime(2026, 10, 17, 12, tzinfo=UTC)


def _actor() -> User:
    return User(
        id=uuid4(),
        email="teacher@example.test",
        role=Role.USER,
        auth_provider=AuthProvider.HULEEDU,
        created_at=_NOW,
        updated_at=_NOW,
    )


def _exam(*, owner: User, title: str, age_days: int) -> SavedExam:
    return SavedExam(
        owner_user_id=owner.id,
        lineage_id=uuid4(),
        course_key=None,
        title=title,
        saved_at=_NOW - timedelta(days=age_days),
        head_vault_file_id=uuid4(),
        document_format_version=9,
        name=f"{title}.provdokument.zip",
        version=3,
    )


def _handler(index: AsyncMock) -> ListUnreadableExamWorkspaceDocumentsHandler:
    return ListUnreadableExamWorkspaceDocumentsHandler(
        index=index, uow=AsyncMock(spec=UnitOfWorkProtocol)
    )


@pytest.mark.asyncio
async def test_returns_only_the_unreadable_listing_newest_first() -> None:
    actor = _actor()
    oldest = _exam(owner=actor, title="Oldest", age_days=9)
    newest = _exam(owner=actor, title="Newest", age_days=0)
    middle = _exam(owner=actor, title="Middle", age_days=4)
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.list_unreadable_for_owner.return_value = [oldest, newest, middle]

    result = await _handler(index).handle(actor=actor)

    assert [document.title for document in result.documents] == ["Newest", "Middle", "Oldest"]
    assert [document.lineage_id for document in result.documents] == [
        newest.lineage_id,
        middle.lineage_id,
        oldest.lineage_id,
    ]
    index.list_unreadable_for_owner.assert_awaited_once_with(owner_user_id=actor.id)
    index.list_for_owner.assert_not_awaited()


@pytest.mark.asyncio
async def test_saved_at_ties_break_by_lineage_id() -> None:
    actor = _actor()
    first = _exam(owner=actor, title="Same moment", age_days=2)
    second = first.model_copy(update={"lineage_id": uuid4(), "head_vault_file_id": uuid4()})
    ordered = sorted((first, second), key=lambda exam: str(exam.lineage_id))
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.list_unreadable_for_owner.return_value = [ordered[1], ordered[0]]

    result = await _handler(index).handle(actor=actor)

    assert [document.lineage_id for document in result.documents] == [
        exam.lineage_id for exam in ordered
    ]


@pytest.mark.asyncio
async def test_maps_head_file_fields_without_readable_extras() -> None:
    actor = _actor()
    exam = _exam(owner=actor, title="Old format", age_days=1)
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.list_unreadable_for_owner.return_value = [exam]

    result = await _handler(index).handle(actor=actor)

    assert len(result.documents) == 1
    (document,) = result.documents
    assert document.lineage_id == exam.lineage_id
    assert document.vault_file_id == exam.head_vault_file_id
    assert document.name == exam.name
    assert document.title == exam.title
    assert document.saved_at == exam.saved_at
    assert set(document.model_dump()) == {
        "lineage_id",
        "vault_file_id",
        "name",
        "title",
        "saved_at",
    }


@pytest.mark.asyncio
async def test_empty_unreadable_listing_returns_no_documents() -> None:
    actor = _actor()
    index = AsyncMock(spec=ExamIndexRepositoryProtocol)
    index.list_unreadable_for_owner.return_value = []

    result = await _handler(index).handle(actor=actor)

    assert result.documents == ()
