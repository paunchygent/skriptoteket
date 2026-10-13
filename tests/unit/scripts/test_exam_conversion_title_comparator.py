"""D12: the exam title is the source heading, or the heading with its printed subtitle."""

from pathlib import Path

from scripts.exam_conversion_eval.compare import compare_native_exam
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    points_line,
    title_without_answer_key,
)
from tests.unit.scripts.exam_conversion_corpus_support import gold_exam, replayed

_REEXAM = "svenska_2_grammatik_omprov_variant_1_med_facit"
_COURSE_EXAM = "svenska_2_kursavslutande_prov_med_facit"


def _passes(stem: str, title: str, *, with_chunks: bool = True) -> bool:
    document, chunks = replayed(stem)
    titled = document.model_copy(update={"title": title})
    comparison = compare_native_exam(gold_exam(stem), titled, chunks if with_chunks else ())
    return bool(comparison.title.passed)


def test_the_gold_title_and_the_heading_alone_pass_when_gold_adds_the_subtitle():
    _, chunks = replayed(_REEXAM)
    heading, subtitle = chunks[0], chunks[1]
    assert gold_exam(_REEXAM).title == f"{heading} — {subtitle}"
    assert _passes(_REEXAM, gold_exam(_REEXAM).title)
    assert _passes(_REEXAM, heading)
    assert _passes(_REEXAM, f"{heading} {subtitle}")


def test_the_heading_alone_and_the_heading_with_its_subtitle_pass_when_gold_is_the_heading():
    _, chunks = replayed(_COURSE_EXAM)
    assert gold_exam(_COURSE_EXAM).title == chunks[0]
    assert _passes(_COURSE_EXAM, chunks[0])
    assert _passes(_COURSE_EXAM, f"{chunks[0]} — {chunks[1]}")


def test_another_title_fails():
    _, chunks = replayed(_REEXAM)
    for title in (
        f"{_REEXAM}.docx",
        f"{chunks[0]} — {chunks[1]} — {chunks[2]}",
        f"{chunks[1]} — {chunks[0]}",
        chunks[1],
        "",
    ):
        assert not _passes(_REEXAM, title), title


def test_a_missing_title_fails_and_fails_the_exam():
    document, chunks = replayed(_REEXAM)
    comparison = compare_native_exam(
        gold_exam(_REEXAM), document.model_copy(update={"title": None}), chunks
    )
    assert not comparison.title.passed
    assert not comparison.passed


def test_without_the_source_chunks_only_the_gold_title_passes():
    _, chunks = replayed(_REEXAM)
    assert _passes(_REEXAM, gold_exam(_REEXAM).title, with_chunks=False)
    assert not _passes(_REEXAM, chunks[0], with_chunks=False)


def test_the_heading_with_a_printed_points_line_fails():
    """A total printed under the heading is no subtitle."""
    stems = [
        path.stem
        for path in sorted(Path("tests/fixtures/exam_conversion/docx_corpus/gold").glob("*.json"))
    ]
    with_total = [(stem, chunks) for stem in stems if points_line((chunks := replayed(stem)[1])[1])]
    assert with_total
    for stem, chunks in with_total:
        heading = title_without_answer_key(chunks[0])
        assert _passes(stem, heading)
        assert not _passes(stem, f"{heading} — {chunks[1]}"), stem
