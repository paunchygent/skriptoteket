"""Cached bytes and chunks of the exam-conversion DOCX corpus.

Parsing one corpus DOCX takes up to a second. The bytes and the chunks are immutable, so each
test process reads and parses each file once, however many tests and cases use it.
"""

from __future__ import annotations

from functools import cache
from pathlib import Path

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_docx_chunker import (  # noqa: E501
    PythonDocxExamChunker,
)

CORPUS = Path("tests/fixtures/exam_conversion/docx_corpus")


@cache
def _docx_bytes(path: Path) -> bytes:
    return path.read_bytes()


@cache
def _docx_chunks(path: Path) -> tuple[DocxChunk, ...]:
    return PythonDocxExamChunker().chunk(content=_docx_bytes(path))


def corpus_docx(exam: str, corpus: Path | None = None) -> bytes:
    return _docx_bytes((corpus or CORPUS) / f"{exam}.docx")


def corpus_chunks(exam: str, corpus: Path | None = None) -> tuple[DocxChunk, ...]:
    return _docx_chunks((corpus or CORPUS) / f"{exam}.docx")
