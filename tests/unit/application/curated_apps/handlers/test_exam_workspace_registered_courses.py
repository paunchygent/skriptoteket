"""Catalog preferences affect ordering, never catalog membership or identity."""

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_courses import (
    GetExamCourseCatalogHandler,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
)
from tests.fixtures.profile_app_continuation_support import (
    ProfileRepositoryStub,
    UnitOfWorkStub,
    UserRepositoryStub,
    seed_huleedu_projection,
)


@pytest.mark.asyncio
async def test_catalog_ranks_actor_preferences_without_losing_other_school_forms() -> None:
    profiles = ProfileRepositoryStub()
    actor = seed_huleedu_projection(users=UserRepositoryStub(), profiles=profiles)
    assert profiles.result is not None
    # Only gymnasiet is selected; grundskolan must remain available to typed search.
    preference = {"school_forms": ["gymnasiet"], "course_keys": ["SVEN2000X", "SVESVE01"]}
    profiles.result = type(profiles.result).model_validate(
        {**profiles.result.model_dump(), "exam_courses": preference}
    )
    handler = GetExamCourseCatalogHandler(profiles=profiles, uow=UnitOfWorkStub())

    response = await handler.handle(actor=actor)

    catalog = load_exam_course_catalog()
    expected_keys = preference["course_keys"] + [
        course.key for course in catalog.courses if course.key not in preference["course_keys"]
    ]
    assert [course.key for course in response.courses] == expected_keys
    assert list(response.registered_course_keys) == preference["course_keys"]
    assert {course.key: course for course in response.courses} == {
        course.key: course for course in catalog.courses
    }
    assert response.generated_at == catalog.generated_at
    assert profiles.get_by_user_id_calls == [actor.id]


@pytest.mark.asyncio
async def test_catalog_without_registered_courses_keeps_complete_snapshot_order() -> None:
    profiles = ProfileRepositoryStub()
    actor = seed_huleedu_projection(users=UserRepositoryStub(), profiles=profiles)
    handler = GetExamCourseCatalogHandler(profiles=profiles, uow=UnitOfWorkStub())

    response = await handler.handle(actor=actor)

    assert tuple(response.courses) == load_exam_course_catalog().courses
    assert list(response.registered_course_keys) == []
