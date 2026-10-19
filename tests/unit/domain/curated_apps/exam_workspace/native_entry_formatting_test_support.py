"""Shared builders for the native entry-formatting tests.

Both the repair tests and the continuation-ownership tests build source chunks with
marked labels and converted produced items the same way; entry ownership is read from
the alignment either way.
"""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeSegment,
    NativeTextSegment,
)


def _as_text(segment: NativeSegment) -> NativeTextSegment:
    assert isinstance(segment, NativeTextSegment)
    return segment


def _source(anchor, lines, *, kind="paragraph", separator="\n", one_paragraph=False):
    text = separator.join(line for line, _ in lines)
    runs = []
    paragraphs = []
    offset = 0
    for line, label in lines:
        runs.append(DocxSourceRun(offset, label, ("bold",)))
        runs.append(DocxSourceRun(offset + len(label), line[len(label) :], ()))
        paragraphs.append(DocxSourceParagraph(offset, line, None))
        offset += len(line) + len(separator)
    if one_paragraph:
        paragraphs = [DocxSourceParagraph(0, text, None)]
    return DocxChunk(anchor, kind, text, text, runs=tuple(runs), paragraphs=tuple(paragraphs))


def _item(kind, chunks, **entries):
    return ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": kind,
            "body": [
                {"segments": [{"kind": "text", "text": "Choose an answer.", "accepted_values": []}]}
            ],
            "key_source": None,
            "facit_text": None,
            "points": None,
            "choices": [],
            **entries,
        }
    )
