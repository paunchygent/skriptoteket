"""Memoise the labeler's source projection, which depends only on the DOCX bytes.

A sweep that converts one exam hundreds of times, changing only the grouping, repeats the same
source-DOCX projection in every conversion. The projection is a pure function of the bytes and
is computed once per test process and document (production converts each document once, so the
cache lives here); every call returns its own copy of the mutable maps. Nothing the pipeline
decides from the grouping, the recordings or the model replies is cached.
"""

from __future__ import annotations

from dataclasses import replace
from functools import cache

import pytest

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.protocols.exam_workspace import LabelerSource

_project_source = PythonDocxLabelerMarkdown.source


@cache
def _projected(content: bytes) -> LabelerSource:
    return _project_source(PythonDocxLabelerMarkdown(), content=content)


def _memoised_source(_labeler: PythonDocxLabelerMarkdown, *, content: bytes) -> LabelerSource:
    cached = _projected(content)
    return replace(cached, images=dict(cached.images), unavailable=dict(cached.unavailable))


def memoise_labeler_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the labeler source projection by its cached twin.

    The producer fills ``images`` and ``unavailable`` with plain dicts, so each call gets fresh
    dict copies; the chunks are frozen and shared.
    """
    monkeypatch.setattr(PythonDocxLabelerMarkdown, "source", _memoised_source)
