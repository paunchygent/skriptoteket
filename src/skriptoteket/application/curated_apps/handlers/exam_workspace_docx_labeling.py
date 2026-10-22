"""Labeling input for one DOCX conversion (TASK-SKRIPT-39-05-04 D14).

Each question reaches the labeler as its faithful source: markdown, with an image of
each block markdown cannot carry. A question holding a block of which no faithful image
could be made is never labeled: it is recorded and converts as free text downstream.
"""

from __future__ import annotations

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_run import (
    DocxConversionRun,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    SourceImage,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_manifest import (
    ExamManifest,
    question_source_anchors,
)
from skriptoteket.protocols.exam_workspace import LabelerSource, LabelerSourceProtocol
from skriptoteket.protocols.item_type_labeler import (
    LabelingItem,
    LabelingRequest,
)


def labeling_request(
    run: DocxConversionRun, manifest: ExamManifest, source: LabelerSourceProtocol
) -> tuple[LabelingRequest, list[str]]:
    """Each question's faithful source, and the questions never labeled for a missing image."""
    labeler_source = source.source(content=run.job.source_docx)
    items: list[LabelingItem] = []
    unlabeled: list[str] = []
    for family in run.families:
        anchors = question_source_anchors(manifest, labeler_source.chunks, family.question_id)
        missing = sorted(anchor for anchor in anchors if anchor in labeler_source.unavailable)
        for anchor in missing:
            run.state.record(
                "labeling",
                "labeler_source_image_unavailable",
                anchors=(anchor,),
                detail=labeler_source.unavailable[anchor],
            )
        if missing:
            unlabeled.append(family.question_id)
        else:
            items.append(_labeling_item(family.question_id, labeler_source, anchors))
    return LabelingRequest(
        job_id=run.job.job_id, items=tuple(items), caller=run.job.caller
    ), unlabeled


def _labeling_item(
    question_id: str, source: LabelerSource, anchors: frozenset[str]
) -> LabelingItem:
    """The question's block markdown in source order, each block image at its place."""
    text = ""
    images: list[SourceImage] = []
    for chunk in source.chunks:
        if chunk.anchor not in anchors:
            continue
        if chunk.anchor in source.images:
            images.append(SourceImage(source.images[chunk.anchor], len(text)))
            continue
        text = f"{text}\n{chunk.marked_text}" if text else chunk.marked_text
    return LabelingItem(item_id=question_id, source_text=text, images=tuple(images))
