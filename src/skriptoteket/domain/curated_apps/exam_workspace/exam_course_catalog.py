"""Official course catalog for exam metadata (TASK-SKRIPT-39-08-01).

Purpose:
    One committed snapshot of Skolverket's currently valid gymnasiet courses
    (GY11 and GY25) and grundskolan subject-and-year-band entries, loaded from
    the package directory without any runtime call to Skolverket, plus the one
    general rule that matches a source document's course hint against it.

Relationships:
    - The snapshot under ``exam_course_catalog_data/`` is produced by
      ``scripts/build_exam_course_catalog.py`` from the Skolverket Syllabus API.
    - ``application.curated_apps.handlers.exam_workspace_courses`` serves the
      catalog to the SPA; the conversion build reads ``match_course_hint`` once
      the native document header exists (after TASK-SKRIPT-39-05-14).
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

SchoolForm = Literal["gymnasiet", "grundskolan"]
GymnasietReform = Literal["GY11", "GY25"]


class ExamCourse(BaseModel):
    """One selectable catalog entry.

    ``key`` is the stable unique identifier stored in exam documents: the
    Skolverket course code for gymnasiet and ``<subject code>/<year band>`` for
    grundskolan. ``name`` is what the teacher reads and what a course hint is
    matched against: the official course name for GY11, subject plus level for
    GY25 ("Engelska nivå 1", D23) and subject plus band for grundskolan
    ("Matematik, åk 7–9"). ``code`` is Skolverket's code as shown in the meta line.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    key: str = Field(min_length=1)
    name: str = Field(min_length=1)
    code: str = Field(min_length=1)
    school_form: SchoolForm
    reform: GymnasietReform | None = None
    points: int | None = Field(default=None, ge=0)
    subject_code: str = Field(min_length=1)
    subject_name: str = Field(min_length=1)
    year_band: str | None = None
    year_band_label: str | None = None


class ExamCourseCatalog(BaseModel):
    """The committed snapshot with its provenance."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generated_at: str
    source: str
    courses: tuple[ExamCourse, ...]


class CourseHintMatch(BaseModel):
    """Outcome of matching one course hint against the catalog (D6, D22, D25).

    ``unique`` preselects ``course``; ``ambiguous`` and ``none`` leave the field
    empty and the hint is shown to the teacher.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["unique", "ambiguous", "none"]
    course: ExamCourse | None = None
    candidates: tuple[ExamCourse, ...] = ()


@lru_cache(maxsize=1)
def load_exam_course_catalog() -> ExamCourseCatalog:
    """Load the committed snapshot once from the package directory."""
    payload = files(__package__).joinpath("exam_course_catalog_data/catalog.json")
    return ExamCourseCatalog.model_validate_json(payload.read_text(encoding="utf-8"))


def _tokens(text: str) -> tuple[str, ...]:
    normalized = "".join("-" if unicodedata.category(c) == "Pd" else c for c in text)
    return tuple(re.findall(r"[^\W_]+", normalized.casefold()))


def _outcome(courses: Sequence[ExamCourse]) -> CourseHintMatch:
    ordered = tuple(sorted(courses, key=lambda course: course.key))
    if len(ordered) == 1:
        return CourseHintMatch(kind="unique", course=ordered[0])
    return CourseHintMatch(kind="ambiguous" if ordered else "none", candidates=ordered)


def match_course_hint(hint: str, courses: Sequence[ExamCourse]) -> CourseHintMatch:
    """Match a source course line against the catalog with one general rule (D25).

    After normalizing case, whitespace and dashes, the hint equals exactly one
    entry's name or code, or contains exactly one maximal whole-token entry name
    or code. Several maximal matches are ``ambiguous``; no match is ``none``.
    """

    hint_tokens = _tokens(hint)
    if not hint_tokens:
        return CourseHintMatch(kind="none")
    exact: dict[str, ExamCourse] = {}
    spans: list[tuple[int, int, ExamCourse]] = []
    for course in courses:
        for text in (course.name, course.code):
            tokens = _tokens(text)
            if not tokens:
                continue
            if tokens == hint_tokens:
                exact[course.key] = course
            for start in range(len(hint_tokens) - len(tokens) + 1):
                end = start + len(tokens)
                if hint_tokens[start:end] == tokens:
                    spans.append((start, end, course))
    if exact:
        return _outcome(tuple(exact.values()))
    maximal = {
        course.key: course
        for start, end, course in spans
        if not any(
            left <= start and end <= right and (left, right) != (start, end)
            for left, right, _ in spans
        )
    }
    return _outcome(tuple(maximal.values()))
