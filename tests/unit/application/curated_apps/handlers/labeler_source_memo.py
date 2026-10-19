"""Memoise the labeler's source projection, which depends only on the DOCX bytes.

A sweep that converts one exam hundreds of times, changing only the grouping, repeats the same
source-DOCX projection in every conversion. The projection is a pure function of the bytes and
returns an immutable value, so each test process computes it once per document (production
converts each document once, so the cache lives here). Nothing the pipeline decides from the
grouping, the recordings or the model replies is cached.
"""

from __future__ import annotations

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
    return _projected(content)


def memoise_labeler_source(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the labeler source projection by its cached twin.

    ``LabelerSource`` is frozen and exposes its images and unavailable reasons as read-only
    mappings; the pipeline only reads them.
    """
    monkeypatch.setattr(PythonDocxLabelerMarkdown, "source", _memoised_source)
