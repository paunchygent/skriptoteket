"""Read the saved-exam index in the teacher's preferred course or date order."""

from __future__ import annotations

from skriptoteket.application.curated_apps.exam_workspace import (
    ExamWorkspaceDocumentGroup,
    ExamWorkspaceDocumentListResponse,
    ExamWorkspaceDocumentSummary,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.exam_index import ExamIndexRepositoryProtocol
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class ListExamWorkspaceDocumentsHandler:
    """List the actor's workspace documents as head-version summaries."""

    def __init__(
        self,
        *,
        index: ExamIndexRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        uow: UnitOfWorkProtocol,
    ) -> None:
        self._index = index
        self._profiles = profiles
        self._uow = uow

    async def handle(self, *, actor: User) -> ExamWorkspaceDocumentListResponse:
        async with self._uow:
            profile = await self._profiles.get_by_user_id(user_id=actor.id)
            if profile is None:
                raise not_found("UserProfile", str(actor.id))
            exams = await self._index.list_for_owner(owner_user_id=actor.id)
        exams.sort(key=lambda exam: (-exam.saved_at.timestamp(), str(exam.lineage_id)))
        documents = tuple(
            ExamWorkspaceDocumentSummary(
                lineage_id=exam.lineage_id,
                version=exam.version,
                vault_file_id=exam.head_vault_file_id,
                name=exam.name,
                saved_at=exam.saved_at,
                title=exam.title,
                course_key=exam.course_key,
            )
            for exam in exams
        )
        if profile.exam_list_ordering == "newest":
            return ExamWorkspaceDocumentListResponse(
                ordering="newest",
                documents=documents,
                groups=(),
            )
        catalog = {course.key: course.name for course in load_exam_course_catalog().courses}
        registered = {
            key: position for position, key in enumerate(profile.exam_courses.course_keys)
        }
        grouped: dict[str | None, list[ExamWorkspaceDocumentSummary]] = {}
        for document in documents:
            grouped.setdefault(document.course_key, []).append(document)

        def group_order(key: str | None) -> tuple[int, int, str, str]:
            if key is None:
                return (2, 0, "", "")
            if key in registered:
                return (0, registered[key], "", key)
            return (1, 0, catalog[key].casefold(), key)

        groups = tuple(
            ExamWorkspaceDocumentGroup(
                course_key=key,
                course_name="Utan kurs" if key is None else catalog[key],
                documents=tuple(grouped[key]),
            )
            for key in sorted(grouped, key=group_order)
        )
        return ExamWorkspaceDocumentListResponse(
            ordering="course",
            groups=groups,
            documents=tuple(document for group in groups for document in group.documents),
        )
