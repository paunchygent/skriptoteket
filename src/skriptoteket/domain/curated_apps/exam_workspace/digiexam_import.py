"""Map bare DigiExam IR to the same saved document as other workspace inputs."""

from __future__ import annotations

import base64
from pathlib import PurePath
from uuid import UUID

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamAnswerKeyProvenance,
    DigiExamItemType,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DigiExamIntermediateExam,
    DigiExamIrItem,
)
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    DEFAULT_WRITING_LINES,
)
from skriptoteket.domain.curated_apps.exam_workspace.container import ExamWorkspaceContainerContent
from skriptoteket.domain.curated_apps.exam_workspace.digiexam_body import (
    digiexam_body,
    digiexam_plain_text,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeParagraph,
    NativeTextSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    ExamCourseChoice,
    NativeExamAsset,
    NativeExamDocument,
    NativeExamDocumentOrigin,
    NativeExamHeader,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_import_record import (
    NativeExamAnswerKeyStep,
    NativeExamChosenTypeStep,
    NativeExamImportRecord,
    NativeExamOriginalWording,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import (
    NativeAnswerKey,
    NativeChoice,
    NativeGap,
    NativeItemReview,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeAnswerKeyOrigin,
    NativeExamItemKind,
    NativeItemReviewState,
    NativeParseOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.points_wording import (
    with_settled_points_wording,
)
from skriptoteket.domain.errors import validation_error

_KINDS = {
    DigiExamItemType.OPEN_ENDED: NativeExamItemKind.FREE_TEXT,
    DigiExamItemType.SINGLE_CHOICE: NativeExamItemKind.SINGLE_CHOICE,
    DigiExamItemType.MULTIPLE_CHOICE: NativeExamItemKind.SINGLE_CHOICE,
    DigiExamItemType.MULTIPLE_RESPONSE: NativeExamItemKind.MULTIPLE_RESPONSE,
    DigiExamItemType.GAP_FILL: NativeExamItemKind.GAP_FILL,
}
_ORIGINS = {
    DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY: NativeAnswerKeyOrigin.SOURCE_PROVIDED,
    DigiExamAnswerKeyProvenance.ABSENT: NativeAnswerKeyOrigin.ABSENT,
    DigiExamAnswerKeyProvenance.NOT_APPLICABLE: NativeAnswerKeyOrigin.NOT_APPLICABLE,
}


def build_native_exam_from_digiexam(
    *,
    exam: DigiExamIntermediateExam,
    document_id: UUID,
    source_sha256: str,
    course: ExamCourseChoice | None = None,
) -> ExamWorkspaceContainerContent:
    """Return revision one and exactly its referenced payloads; never propose keys."""
    items: list[NativeExamItem] = []
    assets: dict[str, NativeExamAsset] = {}
    payloads: dict[str, bytes] = {}
    notes: list[str] = []
    for source in exam.items:
        if source.item_type is DigiExamItemType.UNKNOWN:
            opening = (
                " ".join(
                    digiexam_plain_text(
                        html=source.prompt_html,
                        lines=source.prompt_lines,
                    ).split()
                )
                or source.title
            )
            notes.append(
                f"Fråga {source.sequence} – {opening[:100]}: "
                "frågetypen stöds inte och importerades inte."
            )
            continue
        image_ids: dict[int, str] = {}
        for asset in source.embedded_assets:
            asset_id = f"asset_{asset.sha256[:16]}"
            image_ids[asset.source_image_index] = asset_id
            assets[asset_id] = NativeExamAsset(
                asset_id=asset_id,
                sha256=asset.sha256,
                media_type=asset.media_type,
                byte_length=asset.byte_length,
                width=asset.width_px,
                height=asset.height_px,
            )
            payloads[asset_id] = base64.b64decode(asset.content_base64, validate=True)
        reasons = tuple(
            follow.message
            for follow in exam.manual_follow_ups
            if follow.item_id in {source.item_id, "exam"}
        )
        item = with_settled_points_wording(
            _item(source, sequence=len(items) + 1, image_ids=image_ids, reasons=reasons)
        )
        items.append(item)
    if not items:
        raise validation_error("DigiExam-exporten innehåller inga frågetyper som stöds.")
    referenced = {asset_id for item in items for asset_id in item.body_asset_ids()}
    return ExamWorkspaceContainerContent(
        document=NativeExamDocument(
            document_id=document_id,
            revision=1,
            title=PurePath(exam.source_filename).stem,
            header=NativeExamHeader(course=course),
            items=tuple(items),
            assets=tuple(asset for key, asset in assets.items() if key in referenced),
            origin=NativeExamDocumentOrigin(
                kind="digiexam_import",
                source_filename=exam.source_filename,
                source_sha256=source_sha256,
            ),
        ),
        assets_by_id={key: payload for key, payload in payloads.items() if key in referenced},
        notes=tuple(notes),
    )


def _source_answer_key_wording(source: DigiExamIrItem) -> str | None:
    """Snapshot supplied choice labels or gap values, without inventing a key."""
    if source.answer_key.provenance is not DigiExamAnswerKeyProvenance.DXE_POPULATED_KEY:
        return None
    return "\n".join(
        [
            alternative.title
            for alternative in source.alternatives
            if alternative.id in source.answer_key.correct_alternative_ids
        ]
        + [answer.value for answer in source.answer_key.correct_gap_answers]
    )


def _item(
    source: DigiExamIrItem,
    *,
    sequence: int,
    image_ids: dict[int, str],
    reasons: tuple[str, ...],
) -> NativeExamItem:
    kind = _KINDS[source.item_type]
    origin = _ORIGINS[source.answer_key.provenance]
    gap_ids = {gap.guid: f"gap_{index:03d}" for index, gap in enumerate(source.gaps, start=1)}
    body = digiexam_body(
        html=source.prompt_html,
        lines=source.prompt_lines,
        image_ids=image_ids,
        gap_ids=gap_ids,
    )
    if not body:
        body = (
            NativeParagraph(
                segments=(NativeTextSegment(text=source.title, marks=()),),
                heading_level=None,
            ),
        )
    return NativeExamItem(
        item_id=f"item_{source.sequence:03d}",
        sequence=sequence,
        kind=kind,
        printed_label=source.title,
        body=body,
        points=source.max_score,
        writing_lines=DEFAULT_WRITING_LINES if kind is NativeExamItemKind.FREE_TEXT else None,
        choices=tuple(
            NativeChoice(
                choice_id=f"choice_{alternative.id:03d}",
                body=(
                    NativeParagraph(
                        segments=(NativeTextSegment(text=alternative.title, marks=()),),
                        heading_level=None,
                    ),
                ),
            )
            for alternative in source.alternatives
        ),
        gaps=tuple(
            NativeGap(
                gap_id=gap_ids[gap.guid],
                accepted_values=tuple(
                    answer.value
                    for answer in source.answer_key.correct_gap_answers
                    if answer.guid == gap.guid
                ),
            )
            for gap in source.gaps
        ),
        answer_key=NativeAnswerKey(
            origin=origin,
            correct_choice_ids=tuple(
                f"choice_{value:03d}" for value in source.answer_key.correct_alternative_ids
            ),
        ),
        review=NativeItemReview(
            state=NativeItemReviewState.REVIEW_REQUIRED
            if reasons
            else NativeItemReviewState.REVIEW_COMPLETE,
            parse_origin=NativeParseOrigin.DETERMINISTIC,
            reasons=reasons,
        ),
        import_record=NativeExamImportRecord(
            original_wording=NativeExamOriginalWording(
                question_text=digiexam_plain_text(
                    html=source.prompt_html,
                    lines=source.prompt_lines,
                ),
                answer_key_text=_source_answer_key_wording(source),
            ),
            steps=(
                NativeExamChosenTypeStep(chosen_kind=kind),
                NativeExamAnswerKeyStep(origin=origin),
            ),
        ),
    )
