"""Content-Disposition filename compatibility tests."""

from __future__ import annotations

import pytest

from skriptoteket.application.curated_apps.exam_conversion import build_examnet_qti_filename
from skriptoteket.web.content_disposition import attachment_content_disposition

pytestmark = pytest.mark.unit


def test_ascii_source_filename_with_quotes_uses_extended_filename_parameter() -> None:
    filename = build_examnet_qti_filename(input_filename='Prov "A".dxe')

    assert attachment_content_disposition(filename=filename) == (
        "attachment; filename*=utf-8''Prov%20%22A%22%20-%20QTI.zip"
    )
