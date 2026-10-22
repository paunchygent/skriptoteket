"""Fixture parity, every other export: Exam.net QTI, print HTML and print PDF use the
pictures and carry no Word shapes (D8).

The shared build and its scripted model reply live in the parity test support module.
"""

from __future__ import annotations

import base64
import io
import zipfile

import pytest
from pypdf import PdfReader

from skriptoteket.application.curated_apps.exam_workspace import ExamWorkspaceExportTarget
from skriptoteket.domain.curated_apps.exam_conversion.exam_print_house_template import (
    ExamPrintVariant,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_document import (
    build_print_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.exam_print_html import render_print_html
from tests.unit.infrastructure.curated_apps import (
    exam_workspace_docx_shape_fixture_parity_test_support as parity_support,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_fixture_parity_test_support import (  # noqa: E501
    _CHART_ANCHOR,
    _Q5_ANCHOR,
    _Q6_ANCHOR,
    _export,
    _Import,
)

pytestmark = pytest.mark.unit

imported = parity_support.imported


# --- Case 4: every other export uses the picture (D8) -------------------------------

_SHAPE_MARKERS = (b"wordprocessingGroup", b"wordprocessingShape", b"txbxContent", b"<w:drawing")


def _figure_payloads(imported: _Import) -> list[bytes]:
    return [imported.picture(anchor).payload for anchor in (_Q5_ANCHOR, _Q6_ANCHOR)]


def test_the_exam_net_package_carries_the_pictures_and_no_shapes(imported: _Import) -> None:
    package = _export(
        imported.document, imported.result.assets_by_id, ExamWorkspaceExportTarget.QTI
    )

    with zipfile.ZipFile(io.BytesIO(package)) as archive:
        members = {name: archive.read(name) for name in archive.namelist()}
    for payload in (*_figure_payloads(imported), imported.picture(_CHART_ANCHOR).payload):
        assert list(members.values()).count(payload) == 1
    for name, data in members.items():
        assert not any(marker in data for marker in _SHAPE_MARKERS), name
    items = [data for name, data in members.items() if name.startswith("items/")]
    assert sum(data.count(b"<img") for data in items) == 3


@pytest.mark.parametrize("variant", [ExamPrintVariant.STUDENT, ExamPrintVariant.FACIT])
def test_the_print_html_inlines_the_pictures_and_no_shapes(
    imported: _Import, variant: ExamPrintVariant
) -> None:
    html = render_print_html(
        build_print_document(imported.document, variant=variant),
        assets=imported.document.assets,
        assets_by_id=imported.result.assets_by_id,
    )

    for payload in (*_figure_payloads(imported), imported.picture(_CHART_ANCHOR).payload):
        assert base64.b64encode(payload).decode("ascii") in html
    assert html.count("<img") == 3
    assert not any(marker.decode() in html for marker in _SHAPE_MARKERS)


@pytest.mark.parametrize(
    "target", [ExamWorkspaceExportTarget.PDF, ExamWorkspaceExportTarget.PDF_FACIT]
)
def test_the_print_pdf_draws_the_three_pictures_and_holds_no_shapes(
    imported: _Import, target: ExamWorkspaceExportTarget
) -> None:
    pdf = _export(imported.document, imported.result.assets_by_id, target)

    # WeasyPrint may repeat a picture's stream as a mask; the sizes name the pictures.
    pages = PdfReader(io.BytesIO(pdf)).pages
    sizes = {image.image.size for page in pages for image in page.images if image.image is not None}
    assert sizes == {
        (image.width, image.height)
        for image in (imported.picture(a) for a in (_Q5_ANCHOR, _Q6_ANCHOR, _CHART_ANCHOR))
    }
    assert not any(marker in pdf for marker in _SHAPE_MARKERS)
