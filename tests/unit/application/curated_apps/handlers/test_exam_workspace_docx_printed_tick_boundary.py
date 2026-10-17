"""Synthetic boundary proof: printed grid totals use one scoring/review route."""

import time
from decimal import Decimal
from uuid import uuid4

import pytest
from structlog.testing import capture_logs

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    DocxBuildState,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionJob,
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import native_item
from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedMatchPair,
    ProducedMetadata,
    ProducedParagraph,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import question_families
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import manifest_from_output
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    question_retry_source,
    with_retry_sources,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_plain_text
from tests.unit.application.curated_apps.handlers.docx_pipeline_replay import build_replay

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("route", "ticks", "explicit_questions", "sibling_kind"),
    [
        ("external_heading", 100, False, None),
        ("external_heading", 101, False, None),
        ("external_heading", 101, True, None),
        ("owned_heading", 100, False, None),
        ("owned_heading", 101, True, None),
        ("question_total", 100, False, None),
        ("question_total", 101, True, None),
        ("external_heading", 101, True, NativeExamItemKind.FREE_TEXT),
        ("external_heading", 101, True, NativeExamItemKind.MATCHING),
        ("owned_heading", 101, True, NativeExamItemKind.FREE_TEXT),
        ("owned_heading", 101, True, NativeExamItemKind.MATCHING),
        ("question_total", 101, True, NativeExamItemKind.FREE_TEXT),
        ("question_total", 101, True, NativeExamItemKind.MATCHING),
    ],
)
def test_printed_grid_tick_boundary_keeps_score_or_complete_source_review(
    route: str,
    ticks: int,
    explicit_questions: bool,
    sibling_kind: NativeExamItemKind | None,
) -> None:
    rows = tuple(f"Ord {number}" for number in range(1, ticks + 1))
    source = "Kategorisera varje ord.\n" + "\n".join(rows)
    heading = route != "question_total"
    printed_points = 2 if sibling_kind else 1
    metadata = (
        f"Kategorisering ({printed_points} poäng)" if heading else f"Poäng: {printed_points} poäng"
    )
    chunks: tuple[DocxChunk, ...] = (
        DocxChunk("body:0001", "heading" if heading else "paragraph", metadata, metadata),
        DocxChunk("body:0002", "table", source, source),
    )
    sibling_source = "Förklara hur du valde kategori."
    if sibling_kind:
        chunks += (DocxChunk("body:0003", "paragraph", sibling_source, sibling_source),)
    own = tuple(chunk.anchor for chunk in (chunks if route == "owned_heading" else chunks[1:]))
    produced = ProducedItem(
        source_anchors=("body:0002",),
        outcome="converted",
        review_reason=None,
        kind=NativeExamItemKind.MATCHING,
        key_source="copied",
        facit_text="Alla ord hör till kategori A.",
        body=(
            ProducedParagraph(
                segments=(
                    ProducedSegment(
                        kind="text",
                        text="Kategorisera varje ord.",
                        accepted_values=(),
                    ),
                )
            ),
        ),
        points=None,
        choices=(),
        match_left=rows,
        match_right=("Kategori A", "Kategori B"),
        match_pairs=tuple(ProducedMatchPair(left=row, right="Kategori A") for row in rows),
    )
    state = DocxBuildState(
        job_id=uuid4(),
        document_id=uuid4(),
        filename="kategorisering.docx",
        source_sha256="0" * 64,
        chunks=chunks,
        questions=(own,),
        header_anchors=frozenset() if heading else frozenset({"body:0001"}),
    )
    first = native_item(produced, language="sv")
    first = first.model_copy(
        update={"review": first.review.model_copy(update={"confidence": 0.82})}
    )
    state.accepted.append((first, ("body:0002",)))
    if sibling_kind:
        sibling = produced.model_copy(
            update={
                "source_anchors": ("body:0003",),
                "kind": sibling_kind,
                "points": None if sibling_kind is NativeExamItemKind.MATCHING else 5,
                "match_left": rows if sibling_kind is NativeExamItemKind.MATCHING else (),
                "match_right": produced.match_right
                if sibling_kind is NativeExamItemKind.MATCHING
                else (),
                "match_pairs": produced.match_pairs
                if sibling_kind is NativeExamItemKind.MATCHING
                else (),
            }
        )
        state.accepted.append((native_item(sibling, language="sv"), ("body:0003",)))
    state.claimed.update(chunk.anchor for chunk in chunks)
    if route == "external_heading":
        state.instructions = (
            ProducedMetadata(
                text=metadata,
                points=printed_points,
                source_anchors=("body:0001",),
            ),
        )
    result = state.result(questions=(own,)) if explicit_questions else state.result()
    if heading:
        failures = [event for event in result.events if event.code == "invalid_tick_value"]
        if ticks == 101:
            (failure,) = failures
            assert failure.anchors == own
        else:
            assert not failures
    retry = question_retry_source(
        own_anchors=own,
        key_anchors=(),
        read_anchors=frozenset(),
        chunks=chunks,
        label_kind=NativeExamItemKind.MATCHING,
    )
    document = with_retry_sources(result.document, {anchor: retry for anchor in own})
    if not heading:
        manifest = manifest_from_output(
            {
                "title_anchors": [],
                "header_anchors": [
                    {"anchor": "body:0001", "kind": "question_total", "governs": ["q1"]}
                ],
                "questions": [
                    {
                        "id": "q1",
                        "anchors": list(own),
                        "subpart_anchors": [],
                        "answer_key_anchors": [],
                    }
                ],
                "shared_contexts": [],
            },
            chunks,
        )
        job = DocxConversionJob(
            job_id=state.job_id,
            worker_id="boundary-test",
            document_id=state.document_id,
            filename=state.filename,
            source_sha256=state.source_sha256,
            source_docx=b"",
            chunks=chunks,
            course_key=None,
        )
        run = DocxConversionRun(job, time.monotonic())
        run.state = state
        run.manifest = manifest
        run.families = question_families(manifest, chunks)
        run.own_anchors = {"q1": own}
        run.key_anchors = {"q1": ()}
        run.label_kinds = {"q1": NativeExamItemKind.MATCHING}
        run.filled = ["q1"]
        # No recordings are served: only the production finalization/event path runs.
        pipeline = build_replay("bf26_english_1_unit_test_kap_1_2_med_facit").pipeline
        with capture_logs() as logs:
            outcome = pipeline._final(run, manifest)
        document = outcome.result.document
        failures = [event for event in outcome.result.events if event.code == "invalid_tick_value"]
        logged = [event for event in logs if event.get("code") == "invalid_tick_value"]
        if ticks == 101:
            (failure,) = failures
            assert failure.anchors == own
            (logged_failure,) = logged
            assert logged_failure["job_id"] == str(job.job_id)
        else:
            assert not failures
            assert not logged
    NativeExamDocument.model_validate(document.model_dump())
    (item,) = document.items
    assert item.sequence == 1
    for parent in document.parents:
        assert parent.item_ids == (item.item_id,)
    assert item.retry_source == retry
    assert item.item_id == first.item_id
    assert item.source_anchor == first.source_anchor
    assert item.review.confidence == first.review.confidence
    assert item.points == printed_points
    assert item.points_estimated is False
    assert not any(
        blocker.reason == "missing_points" for blocker in native_export_blockers(document)
    )
    if ticks == 100:
        assert item.kind is NativeExamItemKind.MATCHING
        assert item.tick_points == Decimal("0.01")
        assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        assert not native_export_blockers(document)
    else:
        assert item.kind is NativeExamItemKind.FREE_TEXT
        assert item.tick_points is None
        assert item.review.state is NativeItemReviewState.REVIEW_REQUIRED
        assert item.review.parse_origin is NativeParseOrigin.DETERMINISTIC
        text = body_plain_text(item.body)
        assert text.count(source) == 1
        if sibling_kind:
            assert text.count(sibling_source) == 1
        reasons = " ".join(item.review.reasons)
        assert f"Tryckta {printed_points} poäng" in reasons
        assert "0,01" in reasons
        assert any(
            blocker.reason == "unbuilt_question" for blocker in native_export_blockers(document)
        )
    assert "Poäng:" not in body_plain_text(item.body)
