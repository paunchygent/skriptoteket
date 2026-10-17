"""Profile-backed owned exam course update handler.

Purpose:
    Persist the authenticated teacher's school forms and ordered committed
    catalog keys in their app-local profile so the exam workspace can offer
    the registered courses first.

Relationships:
    - Invoked by `PATCH /api/v1/profile/exam-courses`.
    - Read by the exam workspace course catalog route and the profile read.
"""

from __future__ import annotations

from skriptoteket.application.identity.commands import (
    UpdateExamCoursesCommand,
    UpdateExamCoursesResult,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from skriptoteket.domain.errors import not_found, validation_error
from skriptoteket.domain.identity.models import ExamCourses
from skriptoteket.protocols.clock import ClockProtocol
from skriptoteket.protocols.identity import (
    ProfileRepositoryProtocol,
    UpdateExamCoursesHandlerProtocol,
    UserRepositoryProtocol,
)
from skriptoteket.protocols.uow import UnitOfWorkProtocol


class UpdateExamCoursesHandler(UpdateExamCoursesHandlerProtocol):
    def __init__(
        self,
        *,
        uow: UnitOfWorkProtocol,
        users: UserRepositoryProtocol,
        profiles: ProfileRepositoryProtocol,
        clock: ClockProtocol,
    ) -> None:
        self._uow = uow
        self._users = users
        self._profiles = profiles
        self._clock = clock

    async def handle(self, command: UpdateExamCoursesCommand) -> UpdateExamCoursesResult:
        school_forms = list(dict.fromkeys(command.school_forms))
        course_keys = list(dict.fromkeys(command.course_keys))
        known_keys = {course.key for course in load_exam_course_catalog().courses}
        unknown_keys = [key for key in course_keys if key not in known_keys]
        if unknown_keys:
            raise validation_error(
                f"Unknown exam course keys: {', '.join(unknown_keys)}",
                details={"field": "course_keys"},
            )

        async with self._uow:
            user = await self._users.get_by_id(command.user_id)
            if user is None:
                raise not_found("User", str(command.user_id))

            profile = await self._profiles.get_by_user_id(user_id=command.user_id)
            if profile is None:
                raise not_found("UserProfile", str(command.user_id))

            saved_profile = await self._profiles.update(
                profile=profile.model_copy(
                    update={
                        "exam_courses": ExamCourses(
                            school_forms=school_forms,
                            course_keys=course_keys,
                        ),
                        "updated_at": self._clock.now(),
                    }
                ),
                fields=frozenset({"exam_courses", "updated_at"}),
            )

        return UpdateExamCoursesResult(user=user, profile=saved_profile)
