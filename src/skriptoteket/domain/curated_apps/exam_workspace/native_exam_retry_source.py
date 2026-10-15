"""The stored source one DOCX question is reconverted from (TASK-SKRIPT-39-05-09 D1).

Purpose:
    Capture each grouped question's original conversion source on its item, so one question
    can be reconverted after save and reopen, when the DOCX bytes are gone. The source holds
    the question's own chunks, its answer-key chunks and the read-only shared context it read,
    plus the labeler's first type. Nothing here re-runs grouping or labeling, and nothing
    reconstructs source from an edited item.

Relationships:
    - Written by ``exam_workspace_docx_pipeline`` into every provisional and final document.
    - Read by ``exam_workspace_docx_retry`` through the saved revision's item.
    - Types live on ``native_exam_document`` so the retry source persists with the document.
"""

from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_build import (
    asset_manifest,
    missing_picture_reasons,
    review_source_item,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_batches import QuestionFamily
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxImage,
    DocxMissingImage,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetryImage,
    NativeExamRetryMissingImage,
    NativeExamRetryParagraph,
    NativeExamRetryRun,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
    NativeItemReviewState,
)


def chunk_record(chunk: DocxChunk) -> NativeExamRetryChunk:
    """One chunk as the stored retry source keeps it, formatting runs, paragraphs and
    pictures by reference only."""
    return NativeExamRetryChunk(
        anchor=chunk.anchor,
        kind=chunk.kind,
        text=chunk.text,
        marked_text=chunk.marked_text,
        runs=tuple(
            NativeExamRetryRun(offset=run.offset, text=run.text, marks=run.marks)
            for run in chunk.runs
        ),
        paragraphs=tuple(
            NativeExamRetryParagraph(
                offset=paragraph.offset,
                text=paragraph.text,
                heading_level=paragraph.heading_level,
            )
            for paragraph in chunk.paragraphs
        ),
        images=tuple(
            NativeExamRetryImage(
                asset_id=image.asset_id,
                offset=image.offset,
                marked_offset=image.marked_offset,
            )
            for image in chunk.images
        ),
        missing_images=tuple(
            NativeExamRetryMissingImage(
                reference=image.reference,
                media_type=image.media_type,
                offset=image.offset,
                marked_offset=image.marked_offset,
            )
            for image in chunk.missing_images
        ),
    )


def _missing_images(record: NativeExamRetryChunk) -> tuple[DocxMissingImage, ...]:
    return tuple(
        DocxMissingImage(
            reference=image.reference,
            media_type=image.media_type,
            offset=image.offset,
            marked_offset=image.marked_offset,
        )
        for image in record.missing_images
    )


def chunk_from_record(
    record: NativeExamRetryChunk,
    *,
    assets: Mapping[str, NativeExamAsset],
    payloads: Mapping[str, bytes],
) -> DocxChunk:
    """The stored chunk as the conversion reads it.

    A picture's payload is never stored in the retry source: each reference rebuilds its
    image from the saved document manifest and container payload. A reference the saved
    document no longer carries raises instead of silently losing the picture; the retry
    handler validates the whole source first. The stored runs and paragraphs rebuild the
    chunk's source formatting exactly as the DOCX reader recorded it.
    """
    images: list[DocxImage] = []
    for reference in record.images:
        asset = assets[reference.asset_id]
        image = DocxImage(
            payload=payloads[reference.asset_id],
            media_type=asset.media_type,
            offset=reference.offset,
            marked_offset=reference.marked_offset,
            width=asset.width,
            height=asset.height,
        )
        if image.asset_id != reference.asset_id:
            # The saved payload is not the picture the source stored; fail closed.
            raise ValueError("saved picture payload does not match its stored asset id")
        images.append(image)
    return DocxChunk(
        anchor=record.anchor,
        kind=record.kind,
        text=record.text,
        marked_text=record.marked_text,
        images=tuple(images),
        missing_images=_missing_images(record),
        runs=tuple(
            DocxSourceRun(offset=run.offset, text=run.text, marks=run.marks) for run in record.runs
        ),
        paragraphs=tuple(
            DocxSourceParagraph(
                offset=paragraph.offset,
                text=paragraph.text,
                heading_level=paragraph.heading_level,
            )
            for paragraph in record.paragraphs
        ),
    )


def source_asset_ids(source: NativeExamRetrySource) -> tuple[str, ...]:
    """Every picture the stored source references, own, key and read-only context alike."""
    records = (*source.chunks, *source.key_chunks, *source.context_chunks)
    return tuple(dict.fromkeys(image.asset_id for record in records for image in record.images))


def source_missing_picture_reasons(source: NativeExamRetrySource) -> tuple[str, ...]:
    """Named losses remain review blockers after persistence, including facit/context."""
    records = (*source.chunks, *source.key_chunks, *source.context_chunks)
    return missing_picture_reasons(
        tuple(
            DocxChunk(
                anchor=record.anchor,
                kind=record.kind,
                text=record.text,
                marked_text=record.marked_text,
                missing_images=_missing_images(record),
            )
            for record in records
        )
    )


def _attach_source(item: NativeExamItem, source: NativeExamRetrySource) -> NativeExamItem:
    update = item.model_copy(update={"retry_source": source})
    missing = source_missing_picture_reasons(source)
    if not missing:
        return update
    return update.model_copy(
        update={
            "review": update.review.model_copy(
                update={
                    "state": NativeItemReviewState.REVIEW_REQUIRED,
                    "reasons": tuple(dict.fromkeys((*update.review.reasons, *missing))),
                }
            )
        }
    )


def question_retry_source(
    *,
    own_anchors: tuple[str, ...],
    key_anchors: tuple[str, ...],
    read_anchors: frozenset[str],
    chunks: tuple[DocxChunk, ...],
    label_kind: NativeExamItemKind,
) -> NativeExamRetrySource:
    """The question's original source: own chunks, key chunks and read-only context."""
    position = {chunk.anchor: index for index, chunk in enumerate(chunks)}
    by_anchor = {chunk.anchor: chunk for chunk in chunks}
    context = tuple(
        by_anchor[anchor]
        for anchor in sorted(read_anchors, key=lambda anchor: position[anchor])
        if anchor in by_anchor
    )
    return NativeExamRetrySource(
        chunks=tuple(chunk_record(by_anchor[a]) for a in own_anchors if a in by_anchor),
        key_chunks=tuple(chunk_record(by_anchor[a]) for a in key_anchors if a in by_anchor),
        context_chunks=tuple(chunk_record(chunk) for chunk in context),
        label_kind=label_kind,
    )


def retry_sources_by_anchor(
    *,
    families: tuple[QuestionFamily, ...],
    own_anchors: Mapping[str, tuple[str, ...]],
    key_anchors: Mapping[str, tuple[str, ...]],
    chunks: tuple[DocxChunk, ...],
    label_kinds: Mapping[str, NativeExamItemKind],
) -> dict[str, NativeExamRetrySource]:
    """Every anchor a family claims, mapped to that question's retry source.

    An item's ``source_anchor`` may be any chunk the question's conversion claimed, so the
    map covers each family's claims; a chunk no family claims maps to nothing. The source's
    context is the read-only side: every claimed chunk that is neither the question's own nor
    its answer key — the shared heading, word box or passage the first family owns — together
    with everything the family reads. Pending stays exactly the own and key chunks.
    """
    sources: dict[str, NativeExamRetrySource] = {}
    for family in families:
        question_id = family.question_id
        keys = set(key_anchors.get(question_id, ()))
        # An own chunk the grouping also marks as facit is stored as a key; the retry's item
        # may still hold it as question text.
        own_listed = tuple(a for a in own_anchors.get(question_id, ()) if a not in keys)
        context = (family.claims - set(own_listed) - keys) | family.reads
        source = question_retry_source(
            own_anchors=own_listed,
            key_anchors=key_anchors.get(question_id, ()),
            read_anchors=frozenset(context),
            chunks=chunks,
            label_kind=label_kinds.get(question_id, NativeExamItemKind.FREE_TEXT),
        )
        for anchor in family.claims:
            sources[anchor] = source
    return sources


def with_retry_sources(
    document: NativeExamDocument, sources: Mapping[str, NativeExamRetrySource]
) -> NativeExamDocument:
    """The document with every item that has a known source carrying it."""
    items = tuple(
        item
        if item.source_anchor is None or item.source_anchor not in sources
        else _attach_source(item, sources[item.source_anchor])
        for item in document.items
    )
    return document.model_copy(update={"items": items})


def with_source_assets(
    *,
    document: NativeExamDocument,
    chunks: tuple[DocxChunk, ...],
    assets_by_id: Mapping[str, bytes],
) -> tuple[NativeExamDocument, Mapping[str, bytes]]:
    """The document plus every picture its bodies and retry sources reference, payloads too.

    A picture a student-visible shared instruction body places (a parent or the
    document-global instruction) is delivered material and is counted like an item body.
    A picture only the facit or the read-only context carries is source material: it
    becomes a declared asset the retry source references, never a student-visible
    segment, so the document contract stays whole and no export gains a teacher-only
    picture. The manifest builder counts item bodies, source references and shared
    instruction bodies and fails closed on a picture no chunk carries; the merged
    document is validated before it is used.
    """
    assets, payloads = asset_manifest(
        document.items,
        chunks,
        shared_bodies=(*(parent.instruction for parent in document.parents), document.instructions),
    )
    merged_document = NativeExamDocument.model_validate(
        document.model_copy(update={"assets": assets}).model_dump()
    )
    return merged_document, MappingProxyType({**dict(assets_by_id), **dict(payloads)})


def own_chunks(
    source: NativeExamRetrySource,
    *,
    assets: Mapping[str, NativeExamAsset],
    payloads: Mapping[str, bytes],
) -> tuple[DocxChunk, ...]:
    """The question's own chunks as the conversion reads them, in source order."""
    return tuple(
        chunk_from_record(record, assets=assets, payloads=payloads) for record in source.chunks
    )


def pending_chunks(
    source: NativeExamRetrySource,
    *,
    assets: Mapping[str, NativeExamAsset],
    payloads: Mapping[str, bytes],
) -> tuple[DocxChunk, ...]:
    """Every chunk one retry sends the converter: the question's own and its answer key."""
    return tuple(
        chunk_from_record(record, assets=assets, payloads=payloads)
        for record in (*source.chunks, *source.key_chunks)
    )


def context_chunks(
    source: NativeExamRetrySource,
    *,
    assets: Mapping[str, NativeExamAsset],
    payloads: Mapping[str, bytes],
) -> tuple[DocxChunk, ...]:
    """The read-only shared context one retry sends beside the question's own chunks."""
    return tuple(
        chunk_from_record(record, assets=assets, payloads=payloads)
        for record in source.context_chunks
    )


def replacement_item(*, original: NativeExamItem, produced: NativeExamItem) -> NativeExamItem:
    """The conversion's item as the replacement for ``original``.

    Identity, place, source and provenance stay the original item's; the conversion's content
    replaces the rest. A stale answer-key suggestion never survives: after a kind change its
    key may be invalid, so the teacher's retry starts without it.
    """
    return produced.model_copy(
        update={
            "item_id": original.item_id,
            "sequence": original.sequence,
            "source_anchor": original.source_anchor,
            "retry_source": original.retry_source,
            "ai_suggestion": None,
        }
    )


def source_review_item(
    *,
    original: NativeExamItem,
    source: NativeExamRetrySource,
    assets: Mapping[str, NativeExamAsset],
    payloads: Mapping[str, bytes],
    reason: str,
) -> NativeExamItem:
    """The question's source text as a review item that keeps the original's identity."""
    review = review_source_item(own_chunks(source, assets=assets, payloads=payloads), reason)
    return review.model_copy(
        update={
            "item_id": original.item_id,
            "sequence": original.sequence,
            "source_anchor": original.source_anchor,
            "retry_source": original.retry_source,
            "ai_suggestion": None,
        }
    )
