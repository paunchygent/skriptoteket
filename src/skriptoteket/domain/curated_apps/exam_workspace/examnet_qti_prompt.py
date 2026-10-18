"""Positioned native prompt bodies and their ordered student-visible QTI resources."""

from collections.abc import Mapping

from skriptoteket.domain.curated_apps.exam_conversion.examnet_qti_contracts import (
    ExamNetQtiImageResource,
    ExamNetQtiPromptGap,
    ExamNetQtiPromptImage,
    ExamNetQtiPromptParagraph,
    ExamNetQtiPromptSegment,
    ExamNetQtiPromptText,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_language_labels import ExamExportLabels
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamAsset,
)
from skriptoteket.domain.curated_apps.exam_workspace.shared_body import body_asset_ids
from skriptoteket.domain.errors import DomainError, ErrorCode


def prompt_paragraphs(
    body: tuple[NativeParagraph, ...],
    *,
    gap_ids: tuple[str, ...] = (),
    image_offset: int = 0,
) -> tuple[ExamNetQtiPromptParagraph, ...]:
    """Bind rich placements, marks and heading levels to the declarations' own carriers."""
    gap_indexes = {gap_id: index for index, gap_id in enumerate(gap_ids)}
    image_index = image_offset
    paragraphs: list[ExamNetQtiPromptParagraph] = []
    for paragraph in body:
        segments: list[ExamNetQtiPromptSegment] = []
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment):
                segments.append(ExamNetQtiPromptText(segment.text, segment.marks))
            elif isinstance(segment, NativeAssetSegment):
                segments.append(ExamNetQtiPromptImage(image_index))
                image_index += 1
            else:
                segments.append(ExamNetQtiPromptGap(gap_indexes[segment.gap_id]))
        paragraphs.append(
            ExamNetQtiPromptParagraph(
                segments=tuple(segments),
                heading_level=paragraph.heading_level,
            )
        )
    return tuple(paragraphs)


def body_carries_formatting(body: tuple[NativeParagraph, ...]) -> bool:
    """True when any text run carries a mark or any paragraph declares a heading level.

    The native exporter uses this to choose the rich rendering path, so formatting
    is never dropped for an item that has no picture or gap carrier to trigger it.
    """

    for paragraph in body:
        if paragraph.heading_level is not None:
            return True
        for segment in paragraph.segments:
            if isinstance(segment, NativeTextSegment) and segment.marks:
                return True
    return False


def image_resources(
    body: tuple[NativeParagraph, ...],
    *,
    owner_id: str,
    labels: ExamExportLabels,
    assets: Mapping[str, NativeExamAsset],
    assets_by_id: Mapping[str, bytes],
    first_image_number: int = 1,
) -> tuple[ExamNetQtiImageResource, ...]:
    """Only explicit student carriers enter this pool; retry/facit references do not."""
    resources: list[ExamNetQtiImageResource] = []
    for index, asset_id in enumerate(body_asset_ids(body), start=first_image_number):
        payload = assets_by_id.get(asset_id)
        if payload is None:
            raise DomainError(
                code=ErrorCode.VALIDATION_ERROR,
                message="Exam shared stem references an asset without payload bytes.",
                details={"owner_id": owner_id, "asset_id": asset_id},
            )
        asset = assets[asset_id]
        resources.append(
            ExamNetQtiImageResource(
                asset_id=f"image_{index:03d}",
                filename=f"{owner_id}-image-{index:03d}.png",
                media_type=asset.media_type,
                payload=payload,
                alt_text=labels.image_alt(index),
                source_reference=asset_id,
            )
        )
    return tuple(resources)
