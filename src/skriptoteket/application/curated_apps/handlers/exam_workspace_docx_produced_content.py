"""Transform producer text into student content without source metadata labels.

Ownership and admission stay with the build. These transformations remove header
text and split heading fields before the native builder owns scoring and formatting.
"""

from pydantic import JsonValue

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import (
    ProducedItem,
    ProducedSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.docx_instruction_runs import heading_wording
from skriptoteket.domain.curated_apps.exam_workspace.docx_source_rules import (
    POINT_LABEL,
    QUESTION_HEADING_LABEL,
)


def normalized_content(produced: ProducedItem) -> ProducedItem:
    """Join adjacent text so source labels split across segments remain one line."""
    body = []
    for paragraph in produced.body:
        joined: list[ProducedSegment] = []
        for segment in paragraph.segments:
            if joined and joined[-1].kind == "text" and segment.kind == "text":
                joined[-1] = joined[-1].model_copy(
                    update={"text": (joined[-1].text or "") + (segment.text or "")}
                )
            else:
                joined.append(segment)
        body.append(paragraph.model_copy(update={"segments": tuple(joined)}))
    return produced.model_copy(update={"body": tuple(body)})


def without_header_content(produced: ProducedItem, header_texts: tuple[str, ...]) -> ProducedItem:
    """Remove header wording from a contaminated reply, preserving source anchors.

    The resulting producer contract is validated here; admission owns its ordinary
    source-review outcome if removing metadata leaves no valid student item.
    """

    def clean(value: JsonValue) -> JsonValue:
        if isinstance(value, str):
            for text in header_texts:
                if text:
                    value = value.replace(text, "")
            return value
        if isinstance(value, list):
            return [clean(part) for part in value]
        if isinstance(value, dict):
            return {
                key: clean(part) if key != "source_anchors" else part for key, part in value.items()
            }
        return value

    cleaned = clean(produced.model_dump(mode="json"))
    raw_body = cleaned.get("body") if isinstance(cleaned, dict) else None
    if isinstance(cleaned, dict) and isinstance(raw_body, list):
        paragraphs: list[JsonValue] = []
        for raw_paragraph in raw_body:
            if not isinstance(raw_paragraph, dict):
                continue
            raw_segments = raw_paragraph.get("segments")
            if isinstance(raw_segments, list):
                raw_paragraph["segments"] = [
                    segment
                    for segment in raw_segments
                    if not (
                        isinstance(segment, dict)
                        and segment.get("kind") == "text"
                        and not str(segment.get("text") or "").strip()
                    )
                ]
                if raw_paragraph["segments"]:
                    paragraphs.append(raw_paragraph)
        cleaned["body"] = paragraphs
    return ProducedItem.model_validate(cleaned)


def with_heading_content(produced: ProducedItem, headings: tuple[DocxChunk, ...]) -> ProducedItem:
    """Put printed heading fields in metadata, leaving heading words in the body."""
    if not headings:
        return produced
    label = QUESTION_HEADING_LABEL.match(headings[0].text)
    if label:
        produced = produced.model_copy(
            update={"printed_label": headings[0].text[: label.end()].strip().rstrip(" .):-")}
        )
    body = []
    for paragraph_index, paragraph in enumerate(produced.body):
        segments = []
        for segment_index, segment in enumerate(paragraph.segments):
            if paragraph_index == 0 and segment.kind == "text" and segment.text:
                text = segment.text
                wording = heading_wording(headings[0], None)
                if not wording or wording.casefold() in text.casefold():
                    for point_label in POINT_LABEL.findall(headings[0].text):
                        text = text.replace(point_label, "", 1)
                if segment_index == 0 and label:
                    printed = QUESTION_HEADING_LABEL.match(text)
                    if printed and (printed.group(1) or printed.group(2)) == (
                        label.group(1) or label.group(2)
                    ):
                        text = text[printed.end() :]
                segment = segment.model_copy(update={"text": text})
            segments.append(segment)
        body.append(paragraph.model_copy(update={"segments": tuple(segments)}))
    return produced.model_copy(update={"body": tuple(body)})
