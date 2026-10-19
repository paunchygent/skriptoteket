"""Collecting the points sweep parses no corpus DOCX: its case ids come from a recorded manifest."""

import os
import subprocess
import sys
from textwrap import dedent

import pytest

pytestmark = pytest.mark.unit

_PROBE = dedent(
    """
    import importlib

    from tests.fixtures import docx_corpus

    importlib.import_module(
        "tests.unit.application.curated_apps.handlers"
        ".test_exam_workspace_docx_points_invariance"
    )
    print(docx_corpus._docx_chunks.cache_info().currsize)
    """
)


def test_importing_the_points_sweep_parses_no_corpus_docx():
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        capture_output=True,
        text=True,
        check=True,
        env={**os.environ, "PYTHONPATH": os.pathsep.join(sys.path)},
        timeout=120,
    )
    assert result.stdout.strip().splitlines()[-1] == "0"
