"""Adversarial HTML families: parser, PDF renderer and QTI adapter agree on prompt images."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamParseStatus,
    DigiExamWarningCode,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_pdf_prompt import (
    render_examnet_prompt_html,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_examnet_qti_adapter import (
    build_examnet_qti_items_from_digiexam_ir,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_prompt_repair import (
    PROMPT_IMAGE_PLACEHOLDER_LINE,
    PromptImagePosition,
    prompt_image_positions,
)

pytestmark = pytest.mark.unit

_PNG_BASE64 = (
    "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAIAAACQd1PeAAAADUlEQVR42mNk+M9QDwADhgGA"
    "WjR9awAAAABJRU5ErkJggg=="
)


@dataclass(frozen=True)
class _Family:
    name: str
    body_html: str
    images: tuple[str, ...]
    positions: tuple[PromptImagePosition, ...]
    placeholders: int
    parse_blocked: bool = False


_FAMILIES = (
    _Family(
        "control-quoted-id",
        '<p><img data-image-id="0"></p>',
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
    ),
    _Family(
        "unquoted-id",
        "<p><img data-image-id=0></p>",
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
    ),
    _Family(
        "gt-inside-quoted-alt",
        '<p><img alt="A > B" data-image-id="0"></p>',
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
    ),
    _Family(
        "binding-text-inside-alt",
        """<p><img alt="data-image-id='0'"></p>""",
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=None),),
        1,
        parse_blocked=True,
    ),
    _Family(
        "img-inside-comment",
        '<p>Text</p><!-- <img data-image-id="0"> -->',
        (),
        (),
        0,
    ),
)


def _parse_family(family: _Family):
    question = {
        "id": 1,
        "title": "Bild",
        "about": "Svara.",
        "bodyHTML": family.body_html,
        "images": list(family.images),
        "maxScore": 1,
        "type": 0,
    }
    return DigiExamDxeParser().parse_payload(
        {"exams": [{"questions": [question]}]}, filename=f"{family.name}.dxe"
    )


@pytest.mark.parametrize("family", _FAMILIES, ids=lambda family: family.name)
def test_html_family_is_classified_identically_by_parser_pdf_and_qti(family: _Family) -> None:
    assert prompt_image_positions(family.body_html) == family.positions

    result = _parse_family(family)
    item = result.items[0]
    warning_codes = [warning.code for warning in item.warnings]
    expect_missing = family.placeholders > 0

    assert (DigiExamWarningCode.MISSING_PROMPT_IMAGE in warning_codes) is expect_missing
    assert (DigiExamWarningCode.UNUSED_EMBEDDED_ASSET_PAYLOAD in warning_codes) is (
        family.parse_blocked
    )
    expected_status = (
        DigiExamParseStatus.BLOCKED if family.parse_blocked else DigiExamParseStatus.SUCCESS
    )
    assert result.status == expected_status

    exam = build_digiexam_intermediate_exam(result)
    ir_item = exam.items[0]
    asset_paths = {
        (ir_item.item_id, asset.source_image_index): "images/asset.png"
        for asset in ir_item.embedded_assets
    }
    pdf_prompt = render_examnet_prompt_html(item=ir_item, asset_paths_by_reference=asset_paths)
    assert pdf_prompt.html.count("missing-image-placeholder") == family.placeholders

    qti_item = build_examnet_qti_items_from_digiexam_ir(exam).items[0]
    assert qti_item.prompt_lines.count(PROMPT_IMAGE_PLACEHOLDER_LINE) == family.placeholders


@pytest.mark.parametrize(
    ("html", "expected"),
    [
        pytest.param(
            '<IMG DATA-IMAGE-ID="2"/>',
            (PromptImagePosition(reference_index=2),),
            id="uppercase-self-closing",
        ),
        pytest.param(
            '<img data-image-id="x">',
            (PromptImagePosition(reference_index=None, ambiguous=True),),
            id="non-decimal-binding-is-ambiguous",
        ),
        pytest.param(
            '<img data-image-id="0" data-image-id="1">',
            (PromptImagePosition(reference_index=None, ambiguous=True),),
            id="duplicate-binding-is-ambiguous",
        ),
        pytest.param(
            "<img data-image-id>",
            (PromptImagePosition(reference_index=None),),
            id="valueless-binding-is-unbound",
        ),
        pytest.param(
            '<script><img data-image-id="0"></script><textarea><img></textarea>',
            (),
            id="raw-text-elements-hold-no-image",
        ),
        pytest.param(
            '<imgx data-image-id="0"><p data-image-id="0">',
            (),
            id="other-elements-hold-no-image",
        ),
        pytest.param(None, (), id="no-prompt"),
    ],
)
def test_prompt_image_positions_count_only_real_img_elements(
    html: str | None, expected: tuple[PromptImagePosition, ...]
) -> None:
    assert prompt_image_positions(html) == expected
