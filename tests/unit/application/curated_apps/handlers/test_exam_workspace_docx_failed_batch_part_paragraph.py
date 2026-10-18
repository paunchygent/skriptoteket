"""A failed batch keeps a paragraph part opener as section structure (review-3 N3b, R3-RQ).

Every plan part opener is section structure whatever its Word kind. When a batch's reply
fails, the batch is rebuilt from its source alone; a pending paragraph part opener then opens
its part's parent with its wording without the points label, as on the normal path. The
part's questions are source-review items, and no item holds the opener.
"""

from uuid import UUID

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_assembly import (
    exam_metadata_anchors,
    exam_wide_anchors,
    governed_anchors,
    merge_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_pipeline_batches import (
    failed,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import (
    ConversionBatch,
    question_families,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    ManifestQuestion,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_points_lines import (
    assign_points_lines,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_FAILED_REASON = "Frågan kunde inte tolkas. Kontrollera källtexten manuellt."
_QUESTION_TEXTS = (
    "1. Förklara vad ett substantiv är.",
    "2. Förklara vad ett adjektiv är.",
    "3. Förklara vad ett subjekt är.",
    "4. Förklara vad ett objekt är.",
)
# Each source: its lines in order and the indexes of the four questions' own lines.
_TOTALLED: tuple[tuple[tuple[str, str], ...], tuple[int, ...]] = (
    (
        ("paragraph", "DEL 1: Ordklasser (6 p)"),
        ("paragraph", _QUESTION_TEXTS[0]),
        ("paragraph", _QUESTION_TEXTS[1]),
        ("heading", "DEL 2: Satsdelar (4 p)"),
        ("paragraph", _QUESTION_TEXTS[2]),
        ("paragraph", _QUESTION_TEXTS[3]),
    ),
    (1, 2, 4, 5),
)
# The omprov shape: untotalled paragraph part lines a summary line opens.
_SUMMARISED: tuple[tuple[tuple[str, str], ...], tuple[int, ...]] = (
    (
        ("paragraph", "Del 1: Ordklasser (6 p) Del 2: Satsdelar (4 p)"),
        ("paragraph", "DEL 1: Ordklasser"),
        ("paragraph", _QUESTION_TEXTS[0]),
        ("paragraph", _QUESTION_TEXTS[1]),
        ("paragraph", "DEL 2: Satsdelar"),
        ("paragraph", _QUESTION_TEXTS[2]),
        ("paragraph", _QUESTION_TEXTS[3]),
    ),
    (2, 3, 5, 6),
)


def _failed_document(
    lines: tuple[tuple[str, str], ...], own: tuple[int, ...]
) -> tuple[NativeExamDocument, tuple[DocxChunk, ...]]:
    chunks = tuple(
        DocxChunk(f"body:{index + 1:04d}", kind, text, text)
        for index, (kind, text) in enumerate(lines)
    )
    job = DocxConversionJob(
        job_id=UUID(int=1),
        worker_id="worker",
        document_id=UUID(int=2),
        filename="prov.docx",
        source_sha256="0" * 64,
        source_docx=b"",
        chunks=chunks,
        course_key=None,
    )
    run = DocxConversionRun(job, 0.0)
    manifest = assign_points_lines(
        ExamManifest(
            questions=tuple(
                ManifestQuestion(f"q{number + 1}", (chunks[index].anchor,), (), ())
                for number, index in enumerate(own)
            ),
            contexts=(),
            title_anchors=(),
            header=(),
            invalid_anchors=(),
            duplicate_anchors=(),
            unplaced_anchors=(),
        ),
        chunks,
    )
    run.families = question_families(manifest, chunks)
    for question in manifest.questions:
        run.own_anchors[question.question_id] = question.anchors
        run.key_anchors[question.question_id] = question.key_anchors
    run.kinds = {q.question_id: NativeExamItemKind.FREE_TEXT for q in manifest.questions}
    batch = ConversionBatch(
        batch_id="w1-01",
        kinds=frozenset({NativeExamItemKind.FREE_TEXT}),
        question_ids=tuple(f.question_id for f in run.families),
        claims=frozenset().union(*(f.claims for f in run.families)),
        reads=frozenset(),
    )
    # The batch's reply failed: the pipeline rebuilds it from its source alone.
    outcome = failed(run, batch, "batch_failed", RuntimeError("the reply failed"))
    merge_batch(run.state, outcome.state, run.title_anchors)
    result = run.state.result(
        governed_anchors(run.contexts, run.families),
        tuple(f.question_anchors for f in run.families),
        exam_wide_anchors(run.contexts, run.families),
        exam_metadata_anchors(run.contexts),
    )
    return result.document, chunks


def _texts(paragraphs: tuple[NativeParagraph, ...]) -> list[str]:
    return [
        segment.text
        for paragraph in paragraphs
        for segment in paragraph.segments
        if isinstance(segment, NativeTextSegment)
    ]


@pytest.mark.parametrize(
    ("source", "openers"),
    [
        (_TOTALLED, ("DEL 1: Ordklasser (6 p)",)),
        (_SUMMARISED, ("DEL 1: Ordklasser", "DEL 2: Satsdelar")),
    ],
    ids=["totalled", "summarised"],
)
def test_a_failed_batch_paragraph_part_opener_opens_its_parent(
    source: tuple[tuple[tuple[str, str], ...], tuple[int, ...]],
    openers: tuple[str, ...],
) -> None:
    lines, own = source
    document, chunks = _failed_document(lines, own)

    items = sorted(document.items, key=lambda item: item.sequence)
    assert [item.source_anchor for item in items] == [chunks[i].anchor for i in own]
    assert all(
        item.review.parse_origin is NativeParseOrigin.SOURCE_FALLBACK
        and item.review.reasons == (_FAILED_REASON,)
        for item in items
    )
    for item in items:
        printed = " ".join(item.plain_text_lines())
        assert not any(opener in printed for opener in openers), (
            "a review item holds the part opener"
        )
        assert "DEL" not in printed
    parents = {parent.printed_total: parent for parent in document.parents}
    assert parents[6].item_ids == (items[0].item_id, items[1].item_id)
    assert _texts(parents[6].instruction) == ["DEL 1: Ordklasser"]
    assert parents[4].item_ids == (items[2].item_id, items[3].item_id)
    assert _texts(parents[4].instruction) == ["DEL 2: Satsdelar"]
    assert not _texts(document.instructions)
