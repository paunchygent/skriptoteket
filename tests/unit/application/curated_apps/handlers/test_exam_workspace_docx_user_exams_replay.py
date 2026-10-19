"""The user's two grammar exams convert as the user ruled on 2026-10-18 (TASK-SKRIPT-39-04-12).

Both exams print a header block (name lines, a "Poängöversikt:" label over a one-line
summary of the four part totals, the exam total), four parts of which DEL 1-3 hold several
questions and DEL 4 one, and a closing "— SLUT PÅ PROVET —" line before the reminder to
check the answers. The rulings:

1. DEL 1-4 are parents over their questions; DEL 4 is a parent with one child, like a
   part over several questions, and its line no longer opens its question's body.
2. The summary line is no exam text; its totals are the parts' printed totals.
3. Name, date, class and exam-total lines are header data, never exam text; the exam total
   is the header's printed total, kept even where the questions' points sum to less.
4. "— SLUT PÅ PROVET —" is a print-only line and appears nowhere.
5. The instruction box and the closing reminder are the exam's instructions, shown once.
"""

from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_text_lines
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay

pytestmark = [pytest.mark.unit, pytest.mark.asyncio]

USER_EXAMS = Path("tests/fixtures/exam_conversion/docx_user_exams")
EXAMS = ("omprov_grammatik_sve2", "exempelprov_grammatik_sve2_v2_1")
HEADER_LINES = {
    "omprov_grammatik_sve2": ("Namn:", "Klass:", "Totalt: 70 poäng"),
    "exempelprov_grammatik_sve2_v2_1": ("Namn:", "Datum:", "Totalt: 70 poäng"),
}
LAST_POINTS = {"omprov_grammatik_sve2": 12, "exempelprov_grammatik_sve2_v2_1": 15}
# Omprov prints 70 p in total but its questions print 67 p (DEL 4's question 12 p where the
# summary says 15 p); the workspace's exam-level amber line shows that difference.
ITEM_SUMS = {"omprov_grammatik_sve2": 67, "exempelprov_grammatik_sve2_v2_1": 70}
BOX = "Provet består av fyra delar. Läs varje uppgift noggrant. Skriv tydligt."
REMINDER = "Kontrollera dina svar innan du lämnar in."


_DOCUMENTS: dict[str, NativeExamDocument] = {}


async def _document(exam: str) -> NativeExamDocument:
    """The exam's converted document, replayed once per process; the document is frozen."""
    if exam not in _DOCUMENTS:
        replay = build_replay(exam, root=USER_EXAMS / "recordings", corpus=USER_EXAMS)
        _DOCUMENTS[exam] = (await replay.pipeline.convert(job=replay.job())).result.document
    return _DOCUMENTS[exam]


def _exam_text(document: NativeExamDocument) -> list[str]:
    """Every line a teacher reads as exam text: instructions, parents and item bodies."""
    return [
        *body_text_lines(document.instructions),
        *(line for parent in document.parents for line in body_text_lines(parent.instruction)),
        *(line for item in document.items for line in body_text_lines(item.body)),
    ]


@pytest.mark.parametrize("exam", EXAMS)
async def test_del_1_to_4_are_parents_and_del_4_has_one_child(exam: str) -> None:
    document = await _document(exam)

    items = sorted(document.items, key=lambda item: item.sequence)
    assert len(items) == 9
    assert all(item.review.parse_origin.value == "llm_parsed" for item in items)
    headings = [body_text_lines(parent.instruction)[0] for parent in document.parents]
    assert headings == [
        "DEL 1: MORFEM OCH FRASER",
        "DEL 2: SATSLÖSNING",
        "DEL 3: BISATSER",
        "DEL 4: TEXTANALYS – SPRÅKLIGA DRAG",
    ]
    assert [len(parent.item_ids) for parent in document.parents] == [4, 2, 2, 1]
    last = items[-1]
    assert document.parents[-1].item_ids == (last.item_id,)
    assert body_text_lines(last.body)[0] != "DEL 4: TEXTANALYS – SPRÅKLIGA DRAG"
    assert not [line for line in body_text_lines(last.body) if line.startswith("DEL 4")]


@pytest.mark.parametrize("exam", EXAMS)
async def test_the_part_summary_is_no_exam_text_and_totals_the_parents(exam: str) -> None:
    document = await _document(exam)

    text = _exam_text(document)
    assert not [line for line in text if "Poängöversikt" in line]
    assert not [line for line in text if "Morfem och fraser (20 p)" in line]
    assert [parent.printed_total for parent in document.parents] == [20, 20, 15, 15]
    by_id = {item.item_id: item for item in document.items}
    sums = [sum(by_id[i].points or 0 for i in parent.item_ids) for parent in document.parents]
    # DEL 4's one question keeps the points it prints itself: omprov's summary says 15 p
    # for DEL 4 while its question prints 12 p, so its parent shows the printed difference;
    # exempelprov's question prints the summary's 15 p.
    assert sums == [20, 20, 15, LAST_POINTS[exam]]
    assert max(document.items, key=lambda item: item.sequence).points == LAST_POINTS[exam]


@pytest.mark.parametrize("exam", EXAMS)
async def test_header_lines_are_header_data_never_exam_text(exam: str) -> None:
    document = await _document(exam)

    text = _exam_text(document)
    for header_line in HEADER_LINES[exam]:
        assert not [line for line in text if line.startswith(header_line)]
    assert document.header.printed_total == 70
    assert sum(item.points or 0 for item in document.items) == ITEM_SUMS[exam]


@pytest.mark.parametrize("exam", EXAMS)
async def test_the_end_of_exam_marker_appears_nowhere(exam: str) -> None:
    document = await _document(exam)

    assert not [line for line in _exam_text(document) if "SLUT PÅ PROVET" in line]


@pytest.mark.parametrize("exam", EXAMS)
async def test_the_box_and_the_closing_reminder_are_the_instructions_once(exam: str) -> None:
    document = await _document(exam)

    instructions = body_text_lines(document.instructions)
    assert instructions.count(BOX) == 1
    assert instructions.count(REMINDER) == 1
    text = _exam_text(document)
    assert text.count(BOX) == 1
    assert text.count(REMINDER) == 1


@pytest.mark.parametrize("exam", EXAMS)
async def test_no_item_body_holds_a_lone_score_field_slash(exam: str) -> None:
    document = await _document(exam)

    for item in document.items:
        assert not [line for line in body_text_lines(item.body) if line.strip() == "/"], (
            item.sequence
        )


async def test_omprov_items_keep_their_points_in_sequence_order() -> None:
    document = await _document("omprov_grammatik_sve2")

    items = sorted(document.items, key=lambda item: item.sequence)
    assert [item.points for item in items] == [4, 8, 4, 4, 10, 10, 9, 6, 12]


@pytest.mark.parametrize("exam", EXAMS)
async def test_the_tips_line_keeps_its_slashes(exam: str) -> None:
    document = await _document(exam)

    assert any(
        "verb/nominaliseringar" in line
        for item in document.items
        for line in body_text_lines(item.body)
    )
