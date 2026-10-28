"""A picture cut from a PDF runs the Word import's picture path unchanged (TASK-SKRIPT-39-10-02).

The exam of ``test_exam_workspace_docx_source_images``'s between-questions case, typeset
as a PDF, goes through the production conversion pipeline: grouping sees the picture
chunk, the labeler gets its PNG, the converter places it, and the native document holds
it as the question's picture asset. Only the network is replaced.
"""

import pytest
from pydantic import JsonValue

from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_workspace_pdf_chunker import (  # noqa: E501
    PdfPlumberExamChunker,
)
from tests.unit.application.curated_apps.handlers.docx_source_image_support import (
    BETWEEN_GROUPING,
    PICTURE_STEM,
    convert,
    converted,
    part_image,
    picture_png,
)
from tests.unit.infrastructure.curated_apps.exam_workspace_pdf_test_support import pdf_bytes

pytestmark = pytest.mark.unit


def _between_pdf() -> bytes:
    """body:0003 a picture alone between two questions, as in the Word case."""
    import base64

    picture = base64.b64encode(picture_png()).decode()
    return pdf_bytes(
        "<h1>Bildfrågor</h1>"
        f"<p>1. {PICTURE_STEM}</p>"
        f'<p><img src="data:image/png;base64,{picture}" style="width:120pt;height:60pt"></p>'
        "<p>2. Beskriv vädret i dag.</p>"
    )


@pytest.mark.asyncio
async def test_a_pdf_picture_between_two_questions_reaches_the_labeler_and_the_document():
    content = _between_pdf()
    chunker = PdfPlumberExamChunker()
    source = chunker.chunk(content=content)
    (picture,) = [image for chunk in source.chunks for image in chunk.images]
    asset_id = picture.asset_id
    items = (
        converted(f"1. {PICTURE_STEM}", 2, 3, asset_ids=(asset_id,)),
        converted("2. Beskriv vädret i dag.", 4),
    )
    title: dict[str, JsonValue] = {"text": "Bildfrågor", "source_anchors": ["body:0001"]}

    decisions, provider, outcome = await convert(
        content, BETWEEN_GROUPING, items, title, chunker=chunker
    )

    (grouping,) = [r for r in provider.requests if r.item_id.startswith("docx_grouping")]
    assert f'[body:0003] (drawing) <image asset_id="{asset_id}"/>' in grouping.user_payload
    (labeling,) = decisions
    assert not isinstance(labeling.input, str), "the cut picture must reach the labeler"
    images = [part for message in labeling.input for part in message.content if part.image_url]
    assert [(part_image(part).width, part_image(part).height) for part in images] == [
        (picture.width, picture.height)
    ]
    document = outcome.result.document
    assert [(item.source_anchor, item.review.state.value) for item in document.items] == [
        ("body:0002", "review_complete"),
        ("body:0004", "review_complete"),
    ]
    assert document.items[0].body_asset_ids() == (asset_id,)
    assert [(asset.asset_id, asset.width, asset.height) for asset in document.assets] == [
        (asset_id, picture.width, picture.height)
    ]
    assert outcome.update.pending == ()
