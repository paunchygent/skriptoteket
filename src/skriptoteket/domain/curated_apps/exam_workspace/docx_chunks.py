"""Ordered source text for the exam workspace DOCX conversion lane."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocxChunk:
    """Plain source text for people; marked_text wraps italic runs in <i>...</i> for the model."""

    anchor: str
    kind: str
    text: str
    marked_text: str
