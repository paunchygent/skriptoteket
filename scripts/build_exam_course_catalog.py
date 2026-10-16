"""Generate the packaged course catalog from Skolverket's Syllabus API.

Run ``pdm run build-exam-course-catalog [--check]``. Only this offline
builder contacts Skolverket. ``--raw-dir`` reads recorded responses instead.
Missing source fields deliberately fail the build rather than guessing.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from datetime import date, datetime, timezone
from html.parser import HTMLParser
from os.path import commonprefix
from pathlib import Path
from typing import Literal
from urllib.request import urlopen

from pydantic import BaseModel, ConfigDict, Field

from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    ExamCourse,
    ExamCourseCatalog,
)

OUTPUT = Path("src/skriptoteket/domain/curated_apps/exam_workspace/exam_course_catalog_data")
SOURCE = "https://api.skolverket.se/syllabus"
LIST_URLS = {
    "courses-gy.json": f"{SOURCE}/v1/courses?schooltype=GY&timespan=LATEST",
    "subjects-gy.json": f"{SOURCE}/v1/subjects?schooltype=GY&timespan=LATEST",
    "subjects-gr.json": f"{SOURCE}/v1/subjects?schooltype=GR&timespan=LATEST",
}
REFORMS = {"SUBJECT_SYLLABUS": "GY11", "GRADE_SUBJECT_SYLLABUS": "GY25"}


class SourceRecord(BaseModel):
    model_config = ConfigDict(extra="ignore", strict=True)


class DatedValidity(SourceRecord):
    start_date: date = Field(alias="startDate")
    end_date: date | None = Field(default=None, alias="endDate")


class SubjectParent(DatedValidity):
    subject_code: str = Field(alias="subjectCode")


class CourseRecord(SourceRecord):
    course_code: str = Field(alias="courseCode")
    course_name: str = Field(alias="courseName")
    course_points: str = Field(alias="coursePoints")
    subject_parent: SubjectParent = Field(alias="subjectParent")


class SubjectRecord(DatedValidity):
    code: str
    name: str


class GymnasiumSubject(SubjectRecord):
    type_of_syllabus: Literal["SUBJECT_SYLLABUS", "GRADE_SUBJECT_SYLLABUS"] = Field(
        alias="typeOfSyllabus"
    )


class CentralContent(SourceRecord):
    year: str
    text: str


class SubjectDetail(SubjectRecord):
    central_contents: list[CentralContent] = Field(alias="centralContents")


class CoursesResponse(SourceRecord):
    courses: list[CourseRecord]


class GymnasiumSubjectsResponse(SourceRecord):
    subjects: list[GymnasiumSubject]


class SubjectsResponse(SourceRecord):
    subjects: list[SubjectRecord]


class SubjectDetailResponse(SourceRecord):
    subject: SubjectDetail


class _HeadingParser(HTMLParser):
    """Read headings, including nested markup and HTML entities."""

    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []
        self.headings: list[str] = []
        self.heading: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if self.heading is None and re.fullmatch(r"h[1-6]", tag):
            self.heading = tag
            self.parts = []

    def handle_data(self, data: str) -> None:
        if self.heading is not None:
            self.parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == self.heading:
            self.headings.append(" ".join("".join(self.parts).split()).replace("-", "–"))
            self.heading = None


def _band_label(year: str, contents: list[CentralContent]) -> str:
    band = year.replace("-", "–")
    suffixes: list[str] = []
    for content in contents:
        parser = _HeadingParser()
        parser.feed(content.text)
        matches = [
            heading
            for heading in parser.headings
            if re.search(rf"(?<!\w){re.escape(band)}(?!\w)", heading)
        ]
        if len(matches) != 1:
            raise ValueError(f"Expected one heading for year band {year!r}: {parser.headings!r}")
        suffixes.append(matches[0].partition(band)[2])
    qualifier = commonprefix(suffixes).rstrip(" ,;:")
    return f"åk {band}{qualifier}"


def _valid(subject: DatedValidity, today: date) -> bool:
    return subject.start_date <= today and (subject.end_date is None or subject.end_date >= today)


def map_course_catalog(
    courses_response: CoursesResponse,
    subjects_gy_response: GymnasiumSubjectsResponse,
    subjects_gr_response: SubjectsResponse,
    subject_details: dict[str, SubjectDetailResponse],
    *,
    today: date,
) -> tuple[ExamCourse, ...]:
    """Map recorded API data without network or filesystem access."""
    subjects = {subject.code: subject for subject in subjects_gy_response.subjects}
    entries: list[ExamCourse] = []
    for row in courses_response.courses:
        parent = row.subject_parent
        subject = subjects[parent.subject_code]
        if not _valid(subject, today) or not _valid(parent, today):
            continue
        reform = REFORMS[subject.type_of_syllabus]
        level = row.course_name
        name = f"{subject.name} {level[0].lower()}{level[1:]}" if reform == "GY25" else level
        entries.append(
            ExamCourse(
                key=row.course_code,
                code=row.course_code,
                name=name,
                school_form="gymnasiet",
                reform=reform,
                points=int(row.course_points),
                subject_code=subject.code,
                subject_name=subject.name,
            )
        )
    for gr_subject in subjects_gr_response.subjects:
        if not _valid(gr_subject, today):
            continue
        code = gr_subject.code
        bands: dict[str, list[CentralContent]] = {}
        for content in subject_details[code].subject.central_contents:
            bands.setdefault(content.year, []).append(content)
        for year, contents in bands.items():
            label = _band_label(year, contents)
            entries.append(
                ExamCourse(
                    key=f"{code}/{year}",
                    code=code,
                    name=f"{gr_subject.name}, {label}",
                    school_form="grundskolan",
                    subject_code=code,
                    subject_name=gr_subject.name,
                    year_band=year,
                    year_band_label=label,
                )
            )
    if len({entry.key for entry in entries}) != len(entries):
        raise ValueError("Skolverket returned duplicate course keys")
    return tuple(sorted(entries, key=lambda entry: entry.key))


def _json_bytes(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode()


def build_payloads(
    courses_response: CoursesResponse,
    subjects_gy_response: GymnasiumSubjectsResponse,
    subjects_gr_response: SubjectsResponse,
    subject_details: dict[str, SubjectDetailResponse],
    *,
    today: date,
    generated_at: str,
) -> dict[str, bytes]:
    """Produce deterministic bytes, including provenance, from recorded inputs."""
    courses = map_course_catalog(
        courses_response, subjects_gy_response, subjects_gr_response, subject_details, today=today
    )
    catalog = ExamCourseCatalog(generated_at=generated_at, source=SOURCE, courses=courses)
    urls = [*LIST_URLS.values()]
    urls.extend(f"{SOURCE}/v1/subjects/{code}" for code in sorted(subject_details))
    manifest = {
        "generated_at": generated_at,
        "valid_on": today.isoformat(),
        "source_urls": urls,
        "counts": dict(
            sorted(Counter(course.reform or course.school_form for course in courses).items())
        ),
        "total": len(courses),
    }
    return {
        "catalog.json": _json_bytes(catalog.model_dump(mode="json")),
        "BUILD.json": _json_bytes(manifest),
    }


def check_payloads(output_dir: Path, payloads: dict[str, bytes]) -> list[str]:
    """Return changed or missing outputs without writing anything."""
    return [
        name
        for name, payload in payloads.items()
        if not (output_dir / name).exists() or (output_dir / name).read_bytes() != payload
    ]


def _read_response[Model: BaseModel](
    name: str, url: str, raw_dir: Path | None, model: type[Model]
) -> Model:
    if raw_dir is not None:
        payload = (raw_dir / name).read_bytes()
    else:
        with urlopen(url, timeout=60) as response:
            payload = response.read()
    return model.model_validate_json(payload)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--raw-dir", type=Path, help="Read recorded API responses; never contact the API"
    )
    parser.add_argument("--output-dir", type=Path, default=OUTPUT)
    args = parser.parse_args()
    courses = _read_response(
        "courses-gy.json", LIST_URLS["courses-gy.json"], args.raw_dir, CoursesResponse
    )
    subjects_gy = _read_response(
        "subjects-gy.json", LIST_URLS["subjects-gy.json"], args.raw_dir, GymnasiumSubjectsResponse
    )
    subjects_gr = _read_response(
        "subjects-gr.json", LIST_URLS["subjects-gr.json"], args.raw_dir, SubjectsResponse
    )
    details = {
        subject.code: _read_response(
            f"subj-{subject.code}.json",
            f"{SOURCE}/v1/subjects/{subject.code}",
            args.raw_dir,
            SubjectDetailResponse,
        )
        for subject in subjects_gr.subjects
    }
    generated_at = datetime.now(timezone.utc).isoformat()
    if args.check:
        generated_at = json.loads((args.output_dir / "BUILD.json").read_text())["generated_at"]
    payloads = build_payloads(
        courses,
        subjects_gy,
        subjects_gr,
        details,
        today=date.today(),
        generated_at=generated_at,
    )
    if args.check:
        mismatches = check_payloads(args.output_dir, payloads)
        if mismatches:
            raise SystemExit(f"Course catalog differs: {', '.join(mismatches)}")
        print("Course catalog is current")
    else:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for name, payload in payloads.items():
            (args.output_dir / name).write_bytes(payload)
        print(f"Course catalog written: {args.output_dir}")


if __name__ == "__main__":
    main()
