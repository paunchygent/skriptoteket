"""Adversarial HTML families: parser and PDF renderer agree on prompt images."""

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
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    build_digiexam_intermediate_exam,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_prompt_repair import (
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
    rendered_images: int
    missing_warning: bool
    ambiguous_warning: bool = False
    parse_blocked: bool = False


_FAMILIES = (
    _Family(
        "control-quoted-id",
        '<p><img data-image-id="0"></p>',
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
        1,
        False,
    ),
    _Family(
        "unquoted-id",
        "<p><img data-image-id=0></p>",
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
        1,
        False,
    ),
    _Family(
        "gt-inside-quoted-alt",
        '<p><img alt="A > B" data-image-id="0"></p>',
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
        1,
        False,
    ),
    _Family(
        "binding-text-inside-alt",
        """<p><img alt="data-image-id='0'"></p>""",
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=None),),
        1,
        0,
        True,
        parse_blocked=True,
    ),
    _Family(
        "img-inside-comment",
        '<p>Text</p><!-- <img data-image-id="0"> -->',
        (),
        (),
        0,
        0,
        False,
    ),
    _Family(
        "duplicate-binding",
        '<p><img data-image-id="0" data-image-id="1"></p>',
        (_PNG_BASE64, _PNG_BASE64),
        (PromptImagePosition(reference_index=None, ambiguous=True),),
        1,
        0,
        False,
        ambiguous_warning=True,
        parse_blocked=True,
    ),
    _Family(
        "img-inside-gap-span-bound",
        '<p>Fyll i <span dx-wg-id="1"><img data-image-id="0"></span> här</p>',
        (_PNG_BASE64,),
        (PromptImagePosition(reference_index=0),),
        0,
        1,
        False,
    ),
    _Family(
        "img-inside-gap-span-unbound",
        '<p>Fyll i <span dx-wg-id="1"><img></span> här</p>',
        (),
        (PromptImagePosition(reference_index=None),),
        1,
        0,
        True,
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

    assert (DigiExamWarningCode.MISSING_PROMPT_IMAGE in warning_codes) is family.missing_warning
    assert (
        DigiExamWarningCode.AMBIGUOUS_EMBEDDED_ASSET_BINDING in warning_codes
    ) is family.ambiguous_warning
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
    assert pdf_prompt.html.count('class="prompt-image"') == family.rendered_images


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


def test_pdf_keeps_text_after_a_gap_span_that_holds_an_image() -> None:
    family = next(f for f in _FAMILIES if f.name == "img-inside-gap-span-bound")
    exam = build_digiexam_intermediate_exam(_parse_family(family))
    ir_item = exam.items[0]
    asset_paths = {
        (ir_item.item_id, asset.source_image_index): "images/asset.png"
        for asset in ir_item.embedded_assets
    }

    html = render_examnet_prompt_html(item=ir_item, asset_paths_by_reference=asset_paths).html

    assert html.count("gap-placeholder") == 1
    assert html.endswith(" här</p>")


@pytest.mark.parametrize(
    "void_markup",
    [
        pytest.param("<br>", id="br-start-tag"),
        pytest.param("<br/>", id="br-self-closing"),
        pytest.param("<hr>", id="hr-start-tag"),
        pytest.param("<input>", id="unclosed-input"),
        pytest.param('<input type="text" value="x">', id="unclosed-input-with-attributes"),
        pytest.param("<wbr><br></br>", id="void-start-tags-and-stray-end-tag"),
        pytest.param("<b>fet</b><br><i>kursiv</i>", id="nested-elements-around-void"),
    ],
)
def test_pdf_keeps_text_after_a_gap_span_that_holds_a_void_element(void_markup: str) -> None:
    family = _Family(
        "void-inside-gap-span",
        f'<p>Fyll i <span dx-wg-id="1">{void_markup}</span> här</p>',
        (),
        (),
        0,
        0,
        False,
    )
    exam = build_digiexam_intermediate_exam(_parse_family(family))

    html = render_examnet_prompt_html(item=exam.items[0], asset_paths_by_reference={}).html

    assert html == '<p>Fyll i <span class="gap-placeholder">[____]</span> här</p>'


def test_pdf_keeps_voids_outside_gap_spans_after_a_void_inside_one() -> None:
    family = _Family(
        "void-before-and-after-gap-span",
        '<p>A<br><span dx-wg-id="1"><hr></span>B<br>C</p>',
        (),
        (),
        0,
        0,
        False,
    )
    exam = build_digiexam_intermediate_exam(_parse_family(family))

    html = render_examnet_prompt_html(item=exam.items[0], asset_paths_by_reference={}).html

    assert html == '<p>A<br><span class="gap-placeholder">[____]</span>B<br>C</p>'


def test_pdf_binds_each_image_through_its_own_start_tag_when_the_owner_document_parse_drifts(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # Simulation, not observed behaviour: the owner interprets a multi-image
    # document differently from the renderer's own element walk (here it drops
    # every position after the first). The renderer must still bind per image.
    from skriptoteket.domain.curated_apps.exam_conversion import digiexam_examnet_pdf_prompt

    real_positions = digiexam_examnet_pdf_prompt.prompt_image_positions

    def drifting_positions(prompt_html: str | None) -> tuple[PromptImagePosition, ...]:
        return real_positions(prompt_html)[:1]

    monkeypatch.setattr(digiexam_examnet_pdf_prompt, "prompt_image_positions", drifting_positions)
    family = _Family(
        "two-images",
        '<p><img data-image-id="0"> och <img data-image-id="1"></p>',
        (_PNG_BASE64, _PNG_BASE64),
        (),
        0,
        2,
        False,
    )
    exam = build_digiexam_intermediate_exam(_parse_family(family))
    ir_item = exam.items[0]
    asset_paths = {
        (ir_item.item_id, asset.source_image_index): f"images/asset-{asset.source_image_index}.png"
        for asset in ir_item.embedded_assets
    }

    html = render_examnet_prompt_html(item=ir_item, asset_paths_by_reference=asset_paths).html

    assert 'src="images/asset-0.png"' in html
    assert 'src="images/asset-1.png"' in html
    assert "missing-image-placeholder" not in html


def test_pdf_renders_one_placeholder_for_a_self_closing_gap_span_inside_a_gap_span() -> None:
    family = _Family(
        "self-closing-gap-inside-gap",
        '<p>A <span dx-wg-id="1"><span dx-wg-id="2"/></span> B</p>',
        (),
        (),
        0,
        0,
        False,
    )
    exam = build_digiexam_intermediate_exam(_parse_family(family))

    html = render_examnet_prompt_html(item=exam.items[0], asset_paths_by_reference={}).html

    assert html == '<p>A <span class="gap-placeholder">[____]</span> B</p>'
