"""Serve the committed catalog with the teacher's registered courses first."""

from skriptoteket.application.curated_apps.exam_workspace import ExamCourseCatalogResponse
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.errors import not_found
from skriptoteket.domain.identity.models import User
from skriptoteket.protocols.identity import ProfileRepositoryProtocol
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class GetExamCourseCatalogHandler:
    def __init__(self, *, profiles: ProfileRepositoryProtocol, uow: UnitOfWorkProtocol) -> None:
        self._profiles = profiles
        self._uow = uow

    async def handle(self, *, actor: User) -> ExamCourseCatalogResponse:
        async with self._uow:
            profile = await self._profiles.get_by_user_id(user_id=actor.id)
            if profile is None:
                raise not_found("UserProfile", str(actor.id))
        catalog = load_exam_course_catalog()
        registered = tuple(profile.exam_courses.course_keys)
        positions = {key: index for index, key in enumerate(registered)}
        courses = tuple(
            sorted(catalog.courses, key=lambda course: positions.get(course.key, len(positions)))
        )
        return ExamCourseCatalogResponse(
            generated_at=catalog.generated_at,
            courses=courses,
            registered_course_keys=registered,
        )
