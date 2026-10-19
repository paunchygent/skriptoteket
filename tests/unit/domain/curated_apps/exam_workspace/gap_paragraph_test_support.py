"""Shared builders for the gap-paragraph picture tests (TASK-SKRIPT-39-04-16)."""

from skriptoteket.domain.curated_apps.exam_workspace.docx_ai_contracts import ProducedItem
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
    DocxSourceParagraph,
    DocxSourceRun,
)
from skriptoteket.domain.curated_apps.exam_workspace.source_formatting import (
    SourceFormatting,
)


def chunk(anchor, text, *, heading=None, marks=(), images=()):
    return DocxChunk(
        anchor,
        "paragraph",
        text,
        text,
        images=images,
        runs=(DocxSourceRun(0, text, marks),),
        paragraphs=(DocxSourceParagraph(0, text, heading),),
    )


def picture(asset_id):
    return {"kind": "asset", "text": None, "accepted_values": [], "asset_id": asset_id}


def text(text):
    return {"kind": "text", "text": text, "accepted_values": [], "asset_id": None}


def gap(*accepted):
    return {"kind": "gap", "text": None, "accepted_values": list(accepted), "asset_id": None}


def item(chunks, body, *, printed_label=None, points=None, key_source=None, facit_text=None):
    return ProducedItem.model_validate(
        {
            "source_anchors": [chunk.anchor for chunk in chunks],
            "outcome": "converted",
            "review_reason": None,
            "kind": "gap_fill",
            "printed_label": printed_label,
            "points": points,
            "key_source": key_source,
            "facit_text": facit_text,
            "choices": [],
            "body": body,
        }
    )


def projected(chunks, paragraphs):
    return SourceFormatting(chunks).body(paragraphs)
