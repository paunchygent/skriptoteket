"""Ordered source text for the exam workspace DOCX conversion lane."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DocxChunk:
    anchor: str
    kind: str
    text: str
