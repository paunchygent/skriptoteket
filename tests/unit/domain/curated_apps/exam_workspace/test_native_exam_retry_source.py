"""The stored retry source: capture, rebuild and item replacement (TASK-SKRIPT-39-05-09 D1)."""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxMissingImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_export_rules import (
    native_export_blockers,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetryParagraph,
    NativeExamRetryRun,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_source import (
    chunk_from_record,
    chunk_record,
    own_chunks,
    question_retry_source,
    replacement_item,
    retry_sources_by_anchor,
    source_asset_ids,
    source_review_item,
    with_retry_sources,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeAnswerKeySuggestion,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)

pytestmark = pytest.mark.unit

_ASSET_ID = "asset_0123456789abcdef"
_FINGERPRINT = "a" * 64


def _chunk(anchor: str, text: str, *, kind: str = "paragraph") -> DocxChunk:
    return DocxChunk(anchor=anchor, kind=kind, text=text, marked_text=text)


def _item(
    item_id: str,
    sequence: int,
    *,
    anchor: str | None = "body:0001",
    text: str = "Fråga?",
    suggestion: NativeAnswerKeySuggestion | None = None,
) -> NativeExamItem:
    return NativeExamItem(
        item_id=item_id,
        sequence=sequence,
        kind=NativeExamItemKind.FREE_TEXT,
        body=(
            NativeParagraph(heading_level=None, segments=(NativeTextSegment(text=text, marks=()),)),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
        ),
        source_anchor=anchor,
        ai_suggestion=suggestion,
    )


def _document(items: tuple[NativeExamItem, ...]) -> NativeExamDocument:
    return NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=items,
        origin=NativeExamDocumentOrigin(kind="created"),
    )


def _source(
    *,
    own: tuple[str, ...] = ("body:0001",),
    keys: tuple[str, ...] = (),
    context: tuple[str, ...] = (),
    label_kind: NativeExamItemKind = NativeExamItemKind.FREE_TEXT,
    images: tuple[NativeExamRetryImage, ...] = (),
) -> NativeExamRetrySource:
    return NativeExamRetrySource(
        chunks=tuple(
            NativeExamRetryChunk(
                anchor=anchor,
                kind="paragraph",
                text=anchor,
                marked_text=anchor,
                runs=(NativeExamRetryRun(offset=0, text=anchor, marks=()),),
                paragraphs=(NativeExamRetryParagraph(offset=0, text=anchor, heading_level=None),),
                images=images if index == 0 else (),
            )
            for index, anchor in enumerate(own)
        ),
        key_chunks=tuple(
            NativeExamRetryChunk(
                anchor=anchor,
                kind="paragraph",
                text=anchor,
                marked_text=anchor,
                runs=(NativeExamRetryRun(offset=0, text=anchor, marks=()),),
                paragraphs=(NativeExamRetryParagraph(offset=0, text=anchor, heading_level=None),),
            )
            for anchor in keys
        ),
        context_chunks=tuple(
            NativeExamRetryChunk(
                anchor=anchor,
                kind="paragraph",
                text=anchor,
                marked_text=anchor,
                runs=(NativeExamRetryRun(offset=0, text=anchor, marks=()),),
                paragraphs=(NativeExamRetryParagraph(offset=0, text=anchor, heading_level=None),),
            )
            for anchor in context
        ),
        label_kind=label_kind,
    )


def test_question_source_keeps_own_key_and_context_chunks_in_source_order():
    chunks = (
        _chunk("body:0001", "one"),
        _chunk("body:0002", "two"),
        _chunk("body:0003", "three"),
        _chunk("body:0004", "four"),
    )

    source = question_retry_source(
        own_anchors=("body:0002", "body:0001"),
        key_anchors=("body:0004",),
        read_anchors=frozenset({"body:0003"}),
        chunks=chunks,
        label_kind=NativeExamItemKind.GAP_FILL,
    )

    assert [record.anchor for record in source.chunks] == ["body:0002", "body:0001"]
    assert [record.anchor for record in source.key_chunks] == ["body:0004"]
    assert [record.anchor for record in source.context_chunks] == ["body:0003"]
    assert source.label_kind is NativeExamItemKind.GAP_FILL


def test_retry_sources_map_every_anchor_a_family_claims():
    families = (
        QuestionFamily(
            question_id="q1",
            position=0,
            question_anchors=("body:0001",),
            claims=frozenset({"body:0001", "body:0002"}),
            reads=frozenset({"body:0005"}),
        ),
        QuestionFamily(
            question_id="q2",
            position=1,
            question_anchors=("body:0003",),
            claims=frozenset({"body:0003"}),
            reads=frozenset(),
        ),
    )

    sources = retry_sources_by_anchor(
        families=families,
        own_anchors={"q1": ("body:0001",), "q2": ("body:0003",)},
        key_anchors={"q1": ("body:0002",), "q2": ()},
        chunks=tuple(_chunk(f"body:{n:04d}", "x") for n in range(1, 6)),
        label_kinds={"q1": NativeExamItemKind.FREE_TEXT, "q2": NativeExamItemKind.MATCHING},
    )

    assert set(sources) == {"body:0001", "body:0002", "body:0003"}
    assert [record.anchor for record in sources["body:0002"].key_chunks] == ["body:0002"]
    assert [record.anchor for record in sources["body:0001"].context_chunks] == ["body:0005"]
    assert sources["body:0003"].label_kind is NativeExamItemKind.MATCHING


def test_the_first_owner_of_a_shared_instruction_keeps_it_as_read_only_context():
    families = (
        QuestionFamily(
            question_id="q1",
            position=0,
            question_anchors=("body:0001",),
            claims=frozenset({"body:0001", "body:0005"}),
            reads=frozenset(),
        ),
        QuestionFamily(
            question_id="q2",
            position=1,
            question_anchors=("body:0003",),
            claims=frozenset({"body:0003"}),
            reads=frozenset({"body:0005"}),
        ),
    )

    sources = retry_sources_by_anchor(
        families=families,
        own_anchors={"q1": ("body:0001",), "q2": ("body:0003",)},
        key_anchors={},
        chunks=tuple(_chunk(f"body:{n:04d}", "x") for n in range(1, 6)),
        label_kinds={},
    )

    owner = sources["body:0001"]
    assert [record.anchor for record in owner.chunks] == ["body:0001"]
    assert [record.anchor for record in owner.key_chunks] == []
    assert [record.anchor for record in owner.context_chunks] == ["body:0005"]
    assert [record.anchor for record in sources["body:0003"].context_chunks] == ["body:0005"]


def test_a_missing_label_kind_captures_as_free_text():
    families = (
        QuestionFamily(
            question_id="q1",
            position=0,
            question_anchors=("body:0001",),
            claims=frozenset({"body:0001"}),
            reads=frozenset(),
        ),
    )

    sources = retry_sources_by_anchor(
        families=families,
        own_anchors={"q1": ("body:0001",)},
        key_anchors={},
        chunks=(_chunk("body:0001", "x"),),
        label_kinds={},
    )

    assert sources["body:0001"].label_kind is NativeExamItemKind.FREE_TEXT


@pytest.mark.parametrize("source_part", ["chunks", "key_chunks", "context_chunks"])
def test_missing_picture_records_survive_capture_and_block_export_until_teacher_review(
    source_part: str,
) -> None:
    missing = DocxMissingImage("/word/media/image3.emf", "image/x-emf")
    lost_chunk = DocxChunk(
        "body:0001" if source_part == "chunks" else "body:0008",
        "drawing",
        "",
        "",
        missing_images=(missing,),
    )
    source = question_retry_source(
        own_anchors=("body:0001",),
        key_anchors=(),
        read_anchors=frozenset(),
        chunks=(_chunk("body:0001", "Fråga?"),),
        label_kind=NativeExamItemKind.FREE_TEXT,
    ).model_copy(update={source_part: (chunk_record(lost_chunk),)})
    item = _item("item_001", 1)
    item = item.model_copy(
        update={
            "points": 1,
            "review": item.review.model_copy(update={"parse_origin": NativeParseOrigin.LLM_PARSED}),
        }
    )
    updated = with_retry_sources(_document((item,)), {"body:0001": source})
    restored = NativeExamDocument.model_validate_json(updated.model_dump_json())
    result = restored.items[0]
    assert result.body == item.body
    assert result.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert any("image3.emf" in reason for reason in result.review.reasons)
    assert result.retry_source is not None
    records = {
        "chunks": result.retry_source.chunks,
        "key_chunks": result.retry_source.key_chunks,
        "context_chunks": result.retry_source.context_chunks,
    }[source_part]
    rebuilt = chunk_from_record(records[0], assets={}, payloads={})
    assert rebuilt.missing_images == (missing,)
    assert [blocker.reason for blocker in native_export_blockers(restored)] == ["unbuilt_question"]
    reviewed = result.model_copy(
        update={
            "review": result.review.model_copy(
                update={"state": NativeItemReviewState.REVIEW_COMPLETE}
            )
        }
    )
    assert native_export_blockers(restored.model_copy(update={"items": (reviewed,)})) == ()


def test_with_retry_sources_attaches_only_where_a_known_anchor_starts_the_item():
    document = _document(
        (_item("item_001", 1, anchor="body:0001"), _item("item_002", 2, anchor="body:0002"))
    )
    source = _source()

    updated = with_retry_sources(document, {"body:0001": source})

    assert updated.items[0].retry_source == source
    assert updated.items[1].retry_source is None
    assert updated.items[1] == document.items[1]
    assert updated.model_dump(exclude={"items"}) == document.model_dump(exclude={"items"})


def test_replacement_keeps_identity_and_source_and_drops_a_stale_suggestion():
    suggestion = NativeAnswerKeySuggestion(
        gap_accepted_values=(),
        correct_choice_ids=("choice_001",),
        fingerprint=_FINGERPRINT,
        provider_profile_id="provider",
        model="model",
        prompt_template_version="v1",
    )
    original = _item("item_002", 2, anchor="body:0002", suggestion=suggestion)
    original = original.model_copy(update={"retry_source": _source(own=("body:0002",))})
    produced = _item("item_001", 1, anchor="body:0009", text="Omskriven fråga?")

    replacement = replacement_item(original=original, produced=produced)

    assert replacement.item_id == "item_002"
    assert replacement.sequence == 2
    assert replacement.source_anchor == "body:0002"
    assert replacement.retry_source == original.retry_source
    assert replacement.ai_suggestion is None
    assert replacement.body == produced.body


def test_source_review_item_keeps_identity_and_shows_the_own_source_text():
    original = _item("item_002", 2, anchor="body:0002", text="Gammal text")
    source = _source(own=("body:0002",))
    original = original.model_copy(update={"retry_source": source})

    review = source_review_item(
        original=original,
        source=source,
        assets={},
        payloads={},
        reason="Kunde inte tolkas.",
    )

    assert review.item_id == "item_002"
    assert review.sequence == 2
    assert review.source_anchor == "body:0002"
    assert review.retry_source == original.retry_source
    assert review.ai_suggestion is None
    assert review.review.state is NativeItemReviewState.REVIEW_REQUIRED
    assert review.review.parse_origin is NativeParseOrigin.DETERMINISTIC
    assert review.review.reasons == ("Kunde inte tolkas.",)
    assert review.plain_text_lines() == ("body:0002",)


def test_own_chunks_rebuild_the_question_text_without_its_answer_key():
    source = _source(own=("body:0001", "body:0002"), keys=("body:0003",))

    chunks = own_chunks(source, assets={}, payloads={})

    assert [chunk.anchor for chunk in chunks] == ["body:0001", "body:0002"]


def test_source_asset_ids_cover_own_key_and_context_pictures():
    source = NativeExamRetrySource(
        chunks=(
            NativeExamRetryChunk(
                anchor="body:0001",
                kind="drawing",
                text="",
                marked_text="",
                runs=(),
                paragraphs=(),
                images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=0, marked_offset=0),),
            ),
        ),
        key_chunks=(),
        context_chunks=(),
        label_kind=NativeExamItemKind.FREE_TEXT,
    )

    assert source_asset_ids(source) == (_ASSET_ID,)


def test_a_source_only_picture_is_a_referenced_asset_without_entering_the_body():
    asset = NativeExamAsset(
        asset_id=_ASSET_ID,
        sha256="b" * 64,
        media_type="image/png",
        byte_length=4,
    )
    source = NativeExamRetrySource(
        chunks=(
            NativeExamRetryChunk(
                anchor="body:0001",
                kind="paragraph",
                text="fråga",
                marked_text="fråga",
                runs=(NativeExamRetryRun(offset=0, text="fråga", marks=()),),
                paragraphs=(NativeExamRetryParagraph(offset=0, text="fråga", heading_level=None),),
            ),
        ),
        key_chunks=(
            NativeExamRetryChunk(
                anchor="body:0002",
                kind="drawing",
                text="",
                marked_text="",
                runs=(),
                paragraphs=(),
                images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=0, marked_offset=0),),
            ),
        ),
        context_chunks=(),
        label_kind=NativeExamItemKind.FREE_TEXT,
    )
    item = _item("item_001", 1, anchor="body:0001").model_copy(update={"retry_source": source})

    document = NativeExamDocument(
        document_id=uuid4(),
        revision=1,
        title="Prov",
        items=(item,),
        assets=(asset,),
        origin=NativeExamDocumentOrigin(kind="created"),
    )

    assert document.items[0].body_asset_ids() == ()
    assert document.items[0].source_asset_ids() == (_ASSET_ID,)


def test_a_source_picture_without_a_declared_asset_is_rejected():
    source = _source(images=(NativeExamRetryImage(asset_id=_ASSET_ID, offset=0, marked_offset=0),))
    item = _item("item_001", 1, anchor="body:0001").model_copy(update={"retry_source": source})

    with pytest.raises(ValidationError):
        NativeExamDocument(
            document_id=uuid4(),
            revision=1,
            title="Prov",
            items=(item,),
            origin=NativeExamDocumentOrigin(kind="created"),
        )
