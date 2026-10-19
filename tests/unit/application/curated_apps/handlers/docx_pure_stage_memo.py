"""Memoise the conversion stages whose result depends only on their arguments.

A sweep that converts one exam hundreds of times, changing only the grouping, repeats the same
source-DOCX projection and the same spelling-distance computations in every conversion. Both
stages are pure functions of bytes or strings and return immutable values, so each test process
computes each distinct input once. Nothing the pipeline decides from the grouping, the
recordings or the model replies is cached.
"""

from __future__ import annotations

from functools import cache

import pytest

from skriptoteket.domain.curated_apps.exam_workspace import answer_spelling
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_labeler_markdown import (  # noqa: E501
    PythonDocxLabelerMarkdown,
)
from skriptoteket.protocols.exam_workspace import LabelerSource

_project_source = PythonDocxLabelerMarkdown.source
_memoised_distance = cache(answer_spelling._damerau_levenshtein)  # noqa: SLF001


@cache
def _projected(content: bytes) -> LabelerSource:
    return _project_source(PythonDocxLabelerMarkdown(), content=content)


def _memoised_source(_labeler: PythonDocxLabelerMarkdown, *, content: bytes) -> LabelerSource:
    return _projected(content)


def memoise_pure_conversion_stages(monkeypatch: pytest.MonkeyPatch) -> None:
    """Replace the labeler source projection and the spelling distance by cached twins.

    ``LabelerSource`` is frozen and exposes its images and unavailable reasons as read-only
    mappings; the pipeline only reads them.
    """
    monkeypatch.setattr(PythonDocxLabelerMarkdown, "source", _memoised_source)
    monkeypatch.setattr(answer_spelling, "_damerau_levenshtein", _memoised_distance)
