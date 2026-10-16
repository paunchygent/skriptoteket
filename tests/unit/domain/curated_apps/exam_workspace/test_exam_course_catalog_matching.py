"""One adversarial table over the real snapshot: D25 selects spans, not phrases."""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.exam_course_catalog import (
    load_exam_course_catalog,
    match_course_hint,
)


@pytest.mark.parametrize(
    ("hint", "kind", "keys"),
    [
        ("Svenska 2", "unique", ("SVESVE02",)),
        ("Svenska 2 – kursavslutande prov", "unique", ("SVESVE02",)),
        ("Svenska nivå 2", "unique", ("SVEN2000X",)),
        ("SVESVE02", "unique", ("SVESVE02",)),
        ("  (sVeSvE02):  ", "unique", ("SVESVE02",)),
        ("  SVENSKA\t  2\n", "unique", ("SVESVE02",)),
        ("Prov i [Svenska 2], del A", "unique", ("SVESVE02",)),
        ("Svenska 2 och SVESVE02", "unique", ("SVESVE02",)),
        ("Svenska 20", "none", ()),
        ("xSVESVE02", "none", ()),
        ("SVESVE02x", "none", ()),
        ("Matematik 1", "none", ()),
        ("Svenska", "none", ()),
        ("Matematik, åk 7-9", "unique", ("GRGRMAT01/7-9",)),
        ("Matematik, åk 7—9 – slutprov", "unique", ("GRGRMAT01/7-9",)),
        ("", "none", ()),
        (" \t\n", "none", ()),
        ("Obestämt kursnamn från dokumentet", "none", ()),
        ("Historia 1b och Historia 1a1", "ambiguous", ("HISHIS01a1", "HISHIS01b")),
        ("SVESVE02 / SVEN2000X", "ambiguous", ("SVEN2000X", "SVESVE02")),
        (
            "GRGRSVE01",
            "ambiguous",
            ("GRGRSVE01/1-3", "GRGRSVE01/4-6", "GRGRSVE01/7-9"),
        ),
        # A genuine nested course name: Bild is contained in Bild och form 1b.
        ("Bild och form 1b – slutprov", "unique", ("BILBIL01b",)),
        # Keep the separate shorter span; do not globally discard shorter names.
        ("Bild och form 1b – Bild", "ambiguous", ("BILBIL0", "BILBIL01b")),
    ],
)
def test_hint_matching_never_guesses_from_prefixes_or_discards_disjoint_matches(
    hint: str, kind: str, keys: tuple[str, ...]
) -> None:
    result = match_course_hint(hint, load_exam_course_catalog().courses)

    assert result.kind == kind
    if kind == "unique":
        assert result.course is not None
        assert result.course.key == keys[0]
    else:
        assert result.course is None
    if kind == "ambiguous":
        assert tuple(course.key for course in result.candidates) == keys
    if kind == "none":
        assert result.candidates == ()


def test_ambiguous_candidate_order_does_not_depend_on_catalog_order() -> None:
    courses = load_exam_course_catalog().courses
    hint = "Historia 1b och Historia 1a1"
    assert match_course_hint(hint, courses) == match_course_hint(hint, tuple(reversed(courses)))
