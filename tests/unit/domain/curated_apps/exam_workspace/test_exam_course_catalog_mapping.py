"""Offline catalog mapping against recorded Skolverket rows, not hand-made schemas."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from scripts.build_exam_course_catalog import (
    CoursesResponse,
    GymnasiumSubjectsResponse,
    SourceRecord,
    SubjectDetailResponse,
    SubjectsResponse,
    build_payloads,
    check_payloads,
    map_course_catalog,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    ExamCourseCatalog,
    load_exam_course_catalog,
)

FIXTURES = Path("tests/fixtures/exam_course_catalog")
TODAY = date(2026, 10, 16)
STAMP = "2026-10-16T12:00:00+00:00"


def recorded_inputs() -> tuple[
    CoursesResponse,
    GymnasiumSubjectsResponse,
    SubjectsResponse,
    dict[str, SubjectDetailResponse],
]:
    return (
        CoursesResponse.model_validate_json((FIXTURES / "courses-gy.json").read_bytes()),
        GymnasiumSubjectsResponse.model_validate_json((FIXTURES / "subjects-gy.json").read_bytes()),
        SubjectsResponse.model_validate_json((FIXTURES / "subjects-gr.json").read_bytes()),
        {
            code: SubjectDetailResponse.model_validate_json(
                (FIXTURES / f"subj-{code}.json").read_bytes()
            )
            for code in ("GRGRMSP01", "GRGRSVE01")
        },
    )


def test_recorded_rows_keep_official_names_reforms_points_and_subjects() -> None:
    courses = map_course_catalog(*recorded_inputs(), today=TODAY)
    by_key = {course.key: course for course in courses}

    assert len(courses) == len(by_key) == 14  # Eight GY rows, three bands per GR subject.
    expected = {
        "ENGENG05": ("Engelska 5", "GY11", "ENG", "Engelska"),
        "ENGE1000X": ("Engelska nivå 1", "GY25", "ENGE", "Engelska"),
        "MATMAT01a": ("Matematik 1a", "GY11", "MAT", "Matematik"),
        "MATE1A00X": ("Matematik nivå 1a", "GY25", "MATE", "Matematik"),
        "SVESVE02": ("Svenska 2", "GY11", "SVE", "Svenska"),
        "SVEN2000X": ("Svenska nivå 2", "GY25", "SVEN", "Svenska"),
    }
    for key, (name, reform, subject_code, subject_name) in expected.items():
        course = by_key[key]
        assert (course.name, course.reform, course.subject_code, course.subject_name) == (
            name,
            reform,
            subject_code,
            subject_name,
        )
        assert (course.code, course.points, course.school_form) == (key, 100, "gymnasiet")
        assert course.year_band is None

    for band in ("1-3", "4-6", "7-9"):
        course = by_key[f"GRGRSVE01/{band}"]
        assert course.name == f"Svenska, åk {band.replace('-', '–')}"
        assert (course.code, course.subject_code, course.subject_name) == (
            "GRGRSVE01",
            "GRGRSVE01",
            "Svenska",
        )
        assert (course.year_band, course.school_form, course.reform, course.points) == (
            band,
            "grundskolan",
            None,
            None,
        )


def test_repeated_language_variant_bands_keep_only_the_shared_official_qualifier() -> None:
    courses = map_course_catalog(*recorded_inputs(), today=TODAY)
    modern_languages = [course for course in courses if course.subject_code == "GRGRMSP01"]
    assert len(modern_languages) == 3
    for course in modern_languages:
        qualifier = (
            "inom ramen för skolans val" if course.year_band == "4-9" else "inom ramen för språkval"
        )
        band = str(course.year_band).replace("-", "–")
        assert course.year_band_label == f"åk {band}, {qualifier}"
        assert course.name == f"Moderna språk, åk {band}, {qualifier}"


@pytest.mark.parametrize(
    ("start", "end", "kept"),
    [
        ("2022-07-01", "2030-06-30", True),
        ("2022-07-01", None, True),
        ("2026-10-16", "2026-10-16", True),
        ("2022-07-01", "2026-10-15", False),
        ("2026-10-17", None, False),
    ],
)
def test_subject_validity_uses_both_inclusive_date_boundaries(
    start: str, end: str | None, kept: bool
) -> None:
    inputs = recorded_inputs()
    # These date mutations are adversarial cases based on an actual GY11 subject.
    subject = next(row for row in inputs[1].subjects if row.code == "SVE")
    parent = next(row.subject_parent for row in inputs[0].courses if row.course_code == "SVESVE02")
    for validity in (subject, parent):
        validity.start_date = date.fromisoformat(start)
        validity.end_date = date.fromisoformat(end) if end is not None else None
    keys = {course.key for course in map_course_catalog(*inputs, today=TODAY)}
    assert ("SVESVE02" in keys) is kept
    assert "SVEN2000X" in keys  # A filtered subject must not remove its reform peer.


@pytest.mark.parametrize("end_date", ["0", "false", '""', '"not-a-date"'])
@pytest.mark.parametrize("source", ["courses-gy.json", "subjects-gy.json", "subjects-gr.json"])
def test_source_boundary_rejects_malformed_end_date(source: str, end_date: str) -> None:
    raw = (FIXTURES / source).read_text()
    # Corrupt an actual recorded date; a falsey malformed value must not mean open-ended.
    raw = raw.replace('"endDate": "2030-06-30"', f'"endDate": {end_date}', 1)
    if source == "subjects-gr.json":
        raw = raw.replace('"startDate":', f'"endDate": {end_date}, "startDate":', 1)
    models: dict[str, type[SourceRecord]] = {
        "courses-gy.json": CoursesResponse,
        "subjects-gy.json": GymnasiumSubjectsResponse,
        "subjects-gr.json": SubjectsResponse,
    }
    model = models[source]
    with pytest.raises(ValidationError, match="endDate"):
        model.model_validate_json(raw)


@pytest.mark.parametrize("end_date", ["", '"endDate": null,'])
def test_source_boundary_accepts_absent_or_null_end_date(end_date: str) -> None:
    raw = (FIXTURES / "courses-gy.json").read_text().replace('"endDate": "2030-06-30",', end_date)
    courses, subjects_gy, subjects_gr, details = recorded_inputs()
    courses = CoursesResponse.model_validate_json(raw)
    keys = {
        course.key
        for course in map_course_catalog(courses, subjects_gy, subjects_gr, details, today=TODAY)
    }
    assert "SVESVE02" in keys


def test_recorded_biology_introduction_before_year_heading_is_not_a_band_label() -> None:
    # Real source begins with an h4 introduction before the h3 year-band heading.
    detail = SubjectDetailResponse.model_validate_json(
        (FIXTURES / "subj-GRGRBIO01.json").read_bytes()
    )
    courses = map_course_catalog(
        CoursesResponse(courses=[]),
        GymnasiumSubjectsResponse(subjects=[]),
        SubjectsResponse(subjects=[detail.subject]),
        {"GRGRBIO01": detail},
        today=TODAY,
    )
    assert [(course.key, course.name) for course in courses] == [
        ("GRGRBIO01/1-3", "Biologi, åk 1–3"),
        ("GRGRBIO01/4-6", "Biologi, åk 4–6"),
        ("GRGRBIO01/7-9", "Biologi, åk 7–9"),
    ]


def test_mapping_is_independent_of_api_row_order() -> None:
    inputs = recorded_inputs()
    expected = map_course_catalog(*inputs, today=TODAY)
    inputs[0].courses.reverse()
    inputs[1].subjects.reverse()
    inputs[2].subjects.reverse()
    for detail in inputs[3].values():
        detail.subject.central_contents.reverse()
    assert map_course_catalog(*inputs, today=TODAY) == expected


def test_build_check_accepts_identical_mapping_and_detects_stale_or_missing_outputs(
    tmp_path: Path,
) -> None:
    payloads = build_payloads(*recorded_inputs(), today=TODAY, generated_at=STAMP)
    assert set(payloads) == {"catalog.json", "BUILD.json"}
    catalog = ExamCourseCatalog.model_validate_json(payloads["catalog.json"])
    assert catalog.generated_at == STAMP
    assert catalog.courses == map_course_catalog(*recorded_inputs(), today=TODAY)
    for name, data in payloads.items():
        (tmp_path / name).write_bytes(data)
    assert check_payloads(tmp_path, payloads) == []
    (tmp_path / "catalog.json").write_text('{"courses": []}\n')
    assert check_payloads(tmp_path, payloads) == ["catalog.json"]
    (tmp_path / "BUILD.json").unlink()
    assert set(check_payloads(tmp_path, payloads)) == {"catalog.json", "BUILD.json"}


def test_committed_catalog_loads_once_with_real_reform_and_band_entries() -> None:
    catalog = load_exam_course_catalog()
    assert load_exam_course_catalog() is catalog
    by_key = {course.key: course for course in catalog.courses}
    assert len(by_key) == len(catalog.courses)
    assert by_key["SVESVE02"].name == "Svenska 2"
    assert by_key["SVEN2000X"].name == "Svenska nivå 2"
    assert by_key["GRGRMSP01/4-9"].school_form == "grundskolan"
    assert {course.reform for course in catalog.courses} == {"GY11", "GY25", None}
