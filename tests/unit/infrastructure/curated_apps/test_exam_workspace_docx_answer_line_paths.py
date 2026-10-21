"""The final assembly drops printed answer lines on every reconstruction path (W10, R4.1).

Each case builds its source through the real chunker and asserts BOTH the direct
``assemble_build_result`` path and the application ``admit_batch`` + ``result`` path
with ``body_plain_text``. Gap-bearing paragraphs, picture paragraphs and real
headings stay unchanged; source anchors and review accounting stay as recorded at
the base commit.
"""

import io
from uuid import uuid4

from docx import Document
from docx.document import Document as DocxDocument
from docx.shared import Pt
from PIL import Image
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import assemble_build_result
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    DocxBuildResult,
    ProducedItem,
    ProducedMetadata,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_item import aligned_native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_answer_line_gate import (
    ANSWER_LINE_ONLY_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    body_asset_ids,
    body_plain_text,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

_NO_ITEM_REASON = "AI-tolkningen gav ingen fråga eller rubrik för källstycket."


def _chunked(document: DocxDocument) -> tuple[DocxChunk, ...]:
    stream = io.BytesIO()
    document.save(stream)
    return PythonDocxExamChunker().chunk(content=stream.getvalue())


def _text_para(text: str) -> ProducedParagraph:
    return ProducedParagraph(
        segments=(ProducedSegment(kind="text", text=text, accepted_values=()),)
    )


def _produced(
    anchors: tuple[str, ...],
    *texts: str,
    kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
) -> ProducedItem:
    keyed = kind is not NativeExamItemKind.FREE_TEXT
    return ProducedItem(
        source_anchors=anchors,
        outcome="converted",
        review_reason=None,
        kind=kind,
        printed_label=None,
        key_source="copied" if keyed else None,
        facit_text="svar" if keyed else None,
        body=tuple(_text_para(text) for text in texts),
        points=1,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )


def _metadata(text: str, anchor: str) -> ProducedMetadata:
    return ProducedMetadata(text=text, source_anchors=(anchor,))


def _assemble(
    chunks: tuple[DocxChunk, ...],
    items: tuple[ProducedItem, ...],
    instructions: tuple[ProducedMetadata, ...] = (),
    questions: tuple[tuple[str, ...], ...] | None = None,
    exam_wide: frozenset[str] = frozenset(),
) -> DocxBuildResult:
    aligned = tuple(
        aligned_native_item(
            produced,
            chunks=[chunk for chunk in chunks if chunk.anchor in produced.source_anchors],
            language="sv",
            foreign_chunks=(),
        )
        for produced in items
    )
    return assemble_build_result(
        origin_kind="docx_import",
        document_id=uuid4(),
        filename="synthetic.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        accepted=tuple((entry, produced.source_anchors) for entry, produced in zip(aligned, items)),
        review_reasons={},
        instructions=instructions,
        questions=questions
        if questions is not None
        else tuple(item.source_anchors for item in items),
        exam_wide=exam_wide,
    )


def _admit(
    chunks: tuple[DocxChunk, ...],
    items: tuple[ProducedItem, ...],
    instructions: tuple[ProducedMetadata, ...] = (),
    questions: tuple[tuple[str, ...], ...] | None = None,
    exam_wide: frozenset[str] = frozenset(),
) -> DocxBuildResult:
    state = DocxBuildState(
        origin_kind="docx_import",
        job_id=uuid4(),
        document_id=uuid4(),
        filename="synthetic.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=questions
        if questions is not None
        else (tuple(chunk.anchor for chunk in chunks),),
    )
    payload: dict[str, JsonValue] = {"items": [item.model_dump(mode="json") for item in items]}
    if instructions:
        payload["instructions"] = [entry.model_dump(mode="json") for entry in instructions]
    admit_batch(payload, state)
    return state.result(exam_wide=exam_wide)


def _table_cell_document(first: str, cell_first: str, cell_second: str, last: str) -> DocxDocument:
    document = Document()
    document.add_paragraph(first)
    cell = document.add_table(rows=1, cols=1).cell(0, 0)
    cell.text = cell_first
    cell.add_paragraph(cell_second)
    document.add_paragraph(last)
    return document


def _two_chunk_answer_document() -> DocxDocument:
    document = Document()
    document.add_paragraph("Fråga ett?")
    cell = document.add_table(rows=1, cols=1).cell(0, 0)
    cell.text = "Förklara."
    cell.add_paragraph("_____")
    return document


def test_a_table_cell_instruction_source_drops_the_answer_line_on_both_paths() -> None:
    chunks = _chunked(
        _table_cell_document("1. Beskriv försöket.", "Förklara.", "_____", "Motivera slutsatsen.")
    )
    assert [chunk.kind for chunk in chunks] == ["paragraph", "table", "paragraph"]

    anchors = tuple(chunk.anchor for chunk in chunks)
    produced = _produced(anchors, "1. Beskriv försöket.", "Förklara.", "Motivera slutsatsen.")
    instruction = _metadata(chunks[1].text, chunks[1].anchor)
    expected = "1. Beskriv försöket.\nFörklara.\nMotivera slutsatsen."

    assembled = _assemble(chunks, (produced,), (instruction,), (anchors,))
    assert [body_plain_text(item.body) for item in assembled.document.items] == [expected]

    admitted = _admit(chunks, (produced,), (instruction,), (anchors,))
    assert [body_plain_text(item.body) for item in admitted.document.items] == [expected]


def test_a_size_derived_answer_line_stays_out_on_both_final_paths() -> None:
    document = Document()
    prompt = document.add_paragraph().add_run("Förklara.")
    prompt.font.size = Pt(11)
    line = document.add_paragraph().add_run("_____")
    line.font.size = Pt(22)
    line.underline = True
    chunks = _chunked(document)
    assert chunks[1].paragraphs[0].heading_level is not None

    anchors = tuple(chunk.anchor for chunk in chunks)
    produced = _produced(anchors, "Förklara.", "_____")

    assembled = _assemble(chunks, (produced,), (), (anchors,))
    assert [body_plain_text(item.body) for item in assembled.document.items] == ["Förklara."]

    admitted = _admit(chunks, (produced,), (), (anchors,))
    assert [body_plain_text(item.body) for item in admitted.document.items] == ["Förklara."]


def test_a_part_instruction_drops_the_answer_line_on_both_paths() -> None:
    document = Document()
    cell = document.add_table(rows=1, cols=1).cell(0, 0)
    cell.text = "Del A"
    cell.add_paragraph("_____")
    document.add_paragraph("Fråga ett?")
    document.add_paragraph("Fråga två?")
    chunks = _chunked(document)

    first = _produced((chunks[1].anchor,), "Fråga ett?")
    second = _produced((chunks[2].anchor,), "Fråga två?")
    instruction = _metadata(chunks[0].text, chunks[0].anchor)
    questions = ((chunks[1].anchor,), (chunks[2].anchor,))

    assembled = _assemble(chunks, (first, second), (instruction,), questions)
    assert body_plain_text(assembled.document.parents[0].instruction) == "Del A"
    assert [body_plain_text(item.body) for item in assembled.document.items] == [
        "Fråga ett?",
        "Fråga två?",
    ]

    admitted = _admit(chunks, (first, second), (instruction,), questions)
    assert body_plain_text(admitted.document.parents[0].instruction) == "Del A"
    assert [body_plain_text(item.body) for item in admitted.document.items] == [
        "Fråga ett?",
        "Fråga två?",
    ]


def test_an_omitted_question_review_item_drops_the_answer_line() -> None:
    document = Document()
    document.add_paragraph("Fråga ett?")
    cell = document.add_table(rows=1, cols=1).cell(0, 0)
    cell.text = "Förklara."
    cell.add_paragraph("_____")
    chunks = _chunked(document)
    assert chunks[1].kind == "table"

    produced = _produced((chunks[0].anchor,), "Fråga ett?")
    questions = ((chunks[0].anchor,), (chunks[1].anchor,))

    admitted = _admit(chunks, (produced,), (), questions)
    assert [
        (body_plain_text(item.body), item.review.state) for item in admitted.document.items
    ] == [
        ("Fråga ett?", NativeItemReviewState.REVIEW_COMPLETE),
        ("Förklara.", NativeItemReviewState.REVIEW_REQUIRED),
    ]


def test_a_document_instruction_drops_the_answer_line_on_both_paths() -> None:
    chunks = _chunked(
        _table_cell_document("Fråga ett?", "Skriv svaren nedan.", "_____", "Fråga två?")
    )
    produced = _produced((chunks[0].anchor,), "Fråga ett?")
    other = _produced((chunks[2].anchor,), "Fråga två?")
    questions = ((chunks[0].anchor,), (chunks[2].anchor,))
    exam_wide = frozenset({chunks[1].anchor})

    assembled = _assemble(chunks, (produced, other), (), questions, exam_wide)
    assert body_plain_text(assembled.document.instructions) == "Skriv svaren nedan."

    admitted = _admit(chunks, (produced, other), (), questions, exam_wide)
    assert body_plain_text(admitted.document.instructions) == "Skriv svaren nedan."


def test_a_gap_bearing_paragraph_is_kept_on_both_paths() -> None:
    document = Document()
    document.add_table(rows=1, cols=1).cell(0, 0).text = "Fyll i: ____ år"
    chunks = _chunked(document)

    produced = ProducedItem(
        source_anchors=(chunks[0].anchor,),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.GAP_FILL,
        printed_label=None,
        key_source="copied",
        facit_text="svar",
        body=(
            ProducedParagraph(
                segments=(
                    ProducedSegment(kind="text", text="Fyll i: ", accepted_values=()),
                    ProducedSegment(kind="gap", text=None, accepted_values=("2000",)),
                    ProducedSegment(kind="text", text=" år", accepted_values=()),
                )
            ),
        ),
        points=1,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )
    questions = ((chunks[0].anchor,),)

    assembled = _assemble(chunks, (produced,), (), questions)
    assert [body_plain_text(item.body) for item in assembled.document.items] == ["Fyll i: [___] år"]

    admitted = _admit(chunks, (produced,), (), questions)
    assert [body_plain_text(item.body) for item in admitted.document.items] == ["Fyll i: [___] år"]


def test_a_picture_paragraph_is_kept_on_both_paths() -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (120, 60), (40, 90, 160)).save(buffer, format="PNG")
    payload = buffer.getvalue()
    document = Document()
    paragraph = document.add_paragraph()
    paragraph.add_run("Före ")
    paragraph.add_run().add_picture(io.BytesIO(payload))
    paragraph.add_run(" efter")
    chunks = _chunked(document)
    asset_id = chunks[0].images[0].asset_id

    produced = ProducedItem(
        source_anchors=(chunks[0].anchor,),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.FREE_TEXT,
        printed_label=None,
        key_source=None,
        facit_text=None,
        body=(
            ProducedParagraph(
                segments=(
                    ProducedSegment(kind="text", text="Före ", accepted_values=()),
                    ProducedSegment(kind="asset", text=None, asset_id=asset_id, accepted_values=()),
                    ProducedSegment(kind="text", text=" efter", accepted_values=()),
                )
            ),
        ),
        points=1,
        choices=(),
        match_left=(),
        match_right=(),
        match_pairs=(),
        criteria=(),
    )
    questions = ((chunks[0].anchor,),)

    assembled = _assemble(chunks, (produced,), (), questions)
    assert [body_asset_ids(item.body) for item in assembled.document.items] == [(asset_id,)]

    admitted = _admit(chunks, (produced,), (), questions)
    assert [body_asset_ids(item.body) for item in admitted.document.items] == [(asset_id,)]


def test_a_real_heading_keeps_its_section_behaviour_on_both_paths() -> None:
    document = Document()
    document.add_paragraph("Förklara.")
    document.add_paragraph("Del A", style="Heading 1")
    chunks = _chunked(document)

    anchors = tuple(chunk.anchor for chunk in chunks)
    produced = _produced(anchors, "Förklara.")

    assembled = _assemble(chunks, (produced,), (), (anchors,))
    assert [body_plain_text(item.body) for item in assembled.document.items] == ["Del A\nFörklara."]
    assert assembled.document.parents == ()

    admitted = _admit(chunks, (produced,), (), (anchors,))
    assert [body_plain_text(item.body) for item in admitted.document.items] == ["Del A\nFörklara."]
    assert admitted.document.parents == ()


def test_source_anchors_are_unchanged_by_the_gate() -> None:
    document = Document()
    document.add_paragraph("1. Beskriv försöket.")
    cell = document.add_table(rows=1, cols=1).cell(0, 0)
    cell.text = "Förklara."
    cell.add_paragraph("_____")
    document.add_paragraph("Motivera slutsatsen.")
    document.add_paragraph("Vad heter huvudstaden?")
    chunks = _chunked(document)

    first = _produced(
        (chunks[0].anchor, chunks[1].anchor, chunks[2].anchor),
        "1. Beskriv försöket.",
        "Förklara.",
        "Motivera slutsatsen.",
    )
    second = _produced((chunks[3].anchor,), "Vad heter huvudstaden?")
    instruction = _metadata(chunks[1].text, chunks[1].anchor)
    questions = (
        (chunks[0].anchor, chunks[1].anchor, chunks[2].anchor),
        (chunks[3].anchor,),
    )

    assembled = _assemble(chunks, (first, second), (instruction,), questions)
    assert [item.source_anchor for item in assembled.document.items] == ["body:0001", "body:0004"]

    admitted = _admit(chunks, (first, second), (instruction,), questions)
    assert [item.source_anchor for item in admitted.document.items] == ["body:0001", "body:0004"]


def test_review_accounting_is_unchanged_by_removing_the_unshown_filter() -> None:
    chunks = _chunked(
        _table_cell_document("1. Beskriv försöket.", "Förklara.", "_____", "Motivera slutsatsen.")
    )
    anchors = tuple(chunk.anchor for chunk in chunks)
    produced = _produced(anchors, "1. Beskriv försöket.", "Förklara.", "Motivera slutsatsen.")
    instruction = _metadata(chunks[1].text, chunks[1].anchor)

    admitted = _admit(chunks, (produced,), (instruction,), (anchors,))
    assert [(item.review.state, item.review.reasons) for item in admitted.document.items] == [
        (NativeItemReviewState.REVIEW_COMPLETE, ()),
    ]

    omitted = _admit(
        _chunked(_two_chunk_answer_document()),
        (_produced(("body:0001",), "Fråga ett?"),),
        (),
        (("body:0001",), ("body:0002",)),
    )
    assert [(item.review.state, item.review.reasons) for item in omitted.document.items] == [
        (NativeItemReviewState.REVIEW_COMPLETE, ()),
        (NativeItemReviewState.REVIEW_REQUIRED, (_NO_ITEM_REASON,)),
    ]


def test_an_answer_line_only_body_becomes_review_required_on_both_paths() -> None:
    document = Document()
    document.add_paragraph("_____")
    chunks = _chunked(document)

    only = _produced((chunks[0].anchor,), "_____")
    questions = ((chunks[0].anchor,),)

    assembled = _assemble(chunks, (only,), (), questions)
    assert [
        (body_plain_text(item.body), item.review.state) for item in assembled.document.items
    ] == [("", NativeItemReviewState.REVIEW_REQUIRED)]
    assert assembled.document.items[0].review.reasons.count(ANSWER_LINE_ONLY_REASON) == 1

    admitted = _admit(chunks, (only,), (), questions)
    assert [
        (body_plain_text(item.body), item.review.state) for item in admitted.document.items
    ] == [("", NativeItemReviewState.REVIEW_REQUIRED)]
    assert admitted.document.items[0].review.reasons.count(ANSWER_LINE_ONLY_REASON) == 1


def test_an_answer_line_only_item_beside_a_question_keeps_the_question_untouched() -> None:
    document = Document()
    document.add_paragraph("Fråga ett?")
    document.add_paragraph("_____")
    chunks = _chunked(document)

    first = _produced((chunks[0].anchor,), "Fråga ett?")
    second = _produced((chunks[1].anchor,), "_____")
    questions = ((chunks[0].anchor,), (chunks[1].anchor,))

    assembled = _assemble(chunks, (first, second), (), questions)
    assert [
        (body_plain_text(item.body), item.review.state) for item in assembled.document.items
    ] == [
        ("Fråga ett?", NativeItemReviewState.REVIEW_COMPLETE),
        ("", NativeItemReviewState.REVIEW_REQUIRED),
    ]
    assert assembled.document.items[0].review.reasons == ()
    assert assembled.document.items[1].review.reasons.count(ANSWER_LINE_ONLY_REASON) == 1

    admitted = _admit(chunks, (first, second), (), questions)
    assert [
        (body_plain_text(item.body), item.review.state) for item in admitted.document.items
    ] == [
        ("Fråga ett?", NativeItemReviewState.REVIEW_COMPLETE),
        ("", NativeItemReviewState.REVIEW_REQUIRED),
    ]
    assert admitted.document.items[0].review.reasons == ()
    assert admitted.document.items[1].review.reasons.count(ANSWER_LINE_ONLY_REASON) == 1
