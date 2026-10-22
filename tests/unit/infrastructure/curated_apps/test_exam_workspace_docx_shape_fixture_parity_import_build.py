"""Fixture parity, import and build: ``metodprov_med_bilder.docx`` gives questions 5 and 6
their pictures where the PDF import puts them, and each asset keeps its Word shapes (D5, D11).

The shared build and its scripted model reply live in the parity test support module.
"""

from __future__ import annotations

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import (
    DocxChunk,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_own_instructions import (
    DRAWING_SHOWN,
    LEFT_OUT_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_body import (
    NativeAssetSegment,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeItemReviewState,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)
from tests.unit.infrastructure.curated_apps import (
    exam_workspace_docx_shape_fixture_parity_test_support as parity_support,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_docx_shape_fixture_parity_test_support import (  # noqa: E501
    _CHART_ANCHOR,
    _PDF,
    _Q5_ANCHOR,
    _Q6_ANCHOR,
    _Import,
    _word_chunks,
    _words,
)

pytestmark = pytest.mark.unit

imported = parity_support.imported


def _places(chunks: tuple[DocxChunk, ...]) -> list[tuple[str, str]]:
    """Each drawing's place: the text right before it and right after it."""
    return [
        (_words(chunks[index - 1].text), _words(chunks[index + 1].text))
        for index, chunk in enumerate(chunks)
        if chunk.kind == "drawing"
    ]


# --- Case 1: the places -------------------------------------------------------------


def test_word_and_pdf_imports_put_a_picture_at_each_of_the_three_drawings() -> None:
    docx = _word_chunks()
    pdf = PdfPlumberExamChunker().chunk(content=_PDF.read_bytes())

    assert len(_places(docx)) == 3
    assert _places(docx) == _places(pdf)
    for chunks in (docx, pdf):
        assert [len(chunk.images) for chunk in chunks if chunk.kind == "drawing"] == [1, 1, 1]
    assert [chunk.anchor for chunk in pdf] == [chunk.anchor for chunk in docx]


def test_the_two_drawn_figures_carry_their_word_shapes_and_the_chart_carries_none() -> None:
    chunks = {chunk.anchor: chunk for chunk in _word_chunks()}

    def shapes(anchor: str) -> str | None:
        return chunks[anchor].images[0].docx_shapes

    for anchor in (_Q5_ANCHOR, _Q6_ANCHOR):
        markup = shapes(anchor)
        assert markup is not None
        assert markup.count("<wpg:wgp") == 1, anchor
    assert shapes(_CHART_ANCHOR) is None


# --- Case 2: the build (D5, D11) ----------------------------------------------------


@pytest.mark.parametrize("anchor", [_Q5_ANCHOR, _Q6_ANCHOR])
def test_a_drawn_figure_is_a_picture_in_its_question_and_no_review_item(
    imported: _Import, anchor: str
) -> None:
    image = imported.picture(anchor)
    item = imported.item_with(anchor)

    segments = [segment for paragraph in item.body for segment in paragraph.segments]
    place = next(
        index
        for index, segment in enumerate(segments)
        if isinstance(segment, NativeAssetSegment) and segment.asset_id == image.asset_id
    )
    assert 0 < place < len(segments) - 1
    assert item.review.state is NativeItemReviewState.REVIEW_COMPLETE
    assert item.review.reasons == ()
    assert LEFT_OUT_REASON not in item.review.reasons
    assert DRAWING_SHOWN not in item.review.reasons
    assert imported.result.assets_by_id[image.asset_id] == image.payload


def test_the_assets_of_the_figures_carry_the_word_shapes_and_the_charts_carries_none(
    imported: _Import,
) -> None:
    shapes = {asset.asset_id: asset.docx_shapes for asset in imported.document.assets}

    for anchor in (_Q5_ANCHOR, _Q6_ANCHOR):
        image = imported.picture(anchor)
        assert image.docx_shapes is not None
        assert shapes[image.asset_id] == image.docx_shapes
        assert "<wpg:wgp" in image.docx_shapes
    assert shapes[imported.picture(_CHART_ANCHOR).asset_id] is None
    assert len(shapes) == 3


def test_no_item_of_the_scoped_build_is_a_review_item(imported: _Import) -> None:
    assert len(imported.document.items) == 3
    assert all(
        item.review.state is NativeItemReviewState.REVIEW_COMPLETE
        for item in imported.document.items
    )
