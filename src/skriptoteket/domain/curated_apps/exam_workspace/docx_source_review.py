"""Deterministic source review: the native item that shows raw converter chunks.

Kept apart from the model-driven build so any path may fall back to source review
without importing the build module.
"""

from collections.abc import Iterable

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxMissingImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    printed_points,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import (
    NativeExamItem,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import (
    source_paragraphs,
)


def _missing_picture_reason(missing: DocxMissingImage) -> str:
    return (
        f"Bilden {missing.reference} ({missing.media_type}) kan inte visas i provet. "
        "Granska frågan manuellt."
    )


def missing_picture_reasons(chunks: Iterable[DocxChunk]) -> tuple[str, ...]:
    """One named Swedish review reason per unresolved picture, deduplicated by reference.

    An empty result means no chunk carries a picture the conversion could not show.
    """
    reasons: dict[str, str] = {}
    for chunk in chunks:
        for missing in chunk.missing_images:
            reasons.setdefault(missing.reference, _missing_picture_reason(missing))
    return tuple(reasons.values())


def review_source_item(chunks: tuple[DocxChunk, ...], reason: str) -> NativeExamItem:
    """One teacher-review item holding the plain source text of ``chunks``, one paragraph per
    chunk in source order, whatever the model wrote; it keeps the question's printed points
    and every picture at its exact place in the chunk's text, and names every picture the
    conversion could not show beside the caller's ``reason``."""
    body = source_paragraphs(chunks)
    return NativeExamItem(
        item_id="item_001",
        sequence=1,
        kind=NativeExamItemKind.FREE_TEXT,
        points=printed_points(chunks),
        body=body
        or (
            NativeParagraph(
                heading_level=None, segments=(NativeTextSegment(text="Tomt källstycke.", marks=()),)
            ),
        ),
        answer_key=NativeAnswerKey(origin=NativeAnswerKeyOrigin.NOT_APPLICABLE),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=(reason, *missing_picture_reasons(chunks)),
        ),
        source_anchor=chunks[0].anchor,
    )
