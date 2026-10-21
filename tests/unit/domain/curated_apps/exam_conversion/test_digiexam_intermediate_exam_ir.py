"""Tests for the DigiExam intermediate exam IR contract.

Purpose:
    Prove that completed DigiExam parser outputs map into a renderer-neutral
    intermediate exam representation, ported from Sir Convert-a-Lot
    at revision 41be61a6.

Relationships:
    - Exercises `domain.curated_apps.exam_conversion.digiexam_ir_contracts` as
      the source-to-renderer boundary.
    - Result-PDF evidence extraction and DigiExam PDF-export parsing stay
      outside this walking skeleton.
"""

from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from skriptoteket.domain.curated_apps.exam_conversion.digiexam_contracts import (
    DigiExamItemType,
    DigiExamParseStatus,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_dxe_parser import DigiExamDxeParser
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_ir_contracts import (
    DIGIEXAM_IR_SCHEMA_VERSION,
    DigiExamIrManualFollowUpReason,
    build_digiexam_intermediate_exam,
)
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub.exam_image_readability import (
    PillowEmbeddedImageDecodability,
)

pytestmark = pytest.mark.unit

_DXE_FIXTURE_DIR = Path("tests/fixtures/exam_conversion")
_DXE = _DXE_FIXTURE_DIR / "1772718003-test-samma-prov-i-digiexam.dxe"
_EMBEDDED_IMAGE_DXE = _DXE_FIXTURE_DIR / "sanitized-embedded-image.dxe"


def test_dxe_parser_output_maps_to_renderer_neutral_ir_without_answer_synthesis() -> None:
    parse_result = DigiExamDxeParser(
        image_decodability=PillowEmbeddedImageDecodability()
    ).parse_file(_DXE)

    exam = build_digiexam_intermediate_exam(parse_result)

    assert exam.schema_version == DIGIEXAM_IR_SCHEMA_VERSION
    assert exam.source_filename == _DXE.name
    assert exam.source_producer == "DigiExam .dxe"
    assert exam.parse_status == DigiExamParseStatus.SUCCESS
    assert exam.renderer_ready is True
    assert [item.item_id for item in exam.items] == [
        "item-001",
        "item-002",
        "item-003",
        "item-004",
        "item-005",
        "item-006",
        "item-007",
    ]
    assert [item.digiexam_type_code for item in exam.items] == [0, 1, 1, 2, 2, 2, 3]
    assert [item.item_type for item in exam.items] == [
        DigiExamItemType.OPEN_ENDED,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.SINGLE_CHOICE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.MULTIPLE_RESPONSE,
        DigiExamItemType.GAP_FILL,
    ]
    assert exam.items[1].options[1] == "Andra alternativet"
    assert [gap.guid for gap in exam.items[-1].gaps] == [
        "84ef31ef-d257-4bb2-9e27-d8bcba4ac1e1",
        "21d786a3-2f14-49f1-8ffc-388f06d9a20c",
        "b011fc52-c9b2-4d74-aa78-e94035e0599b",
    ]
    assert all(item.answer_key.correct_alternative_ids == () for item in exam.items[1:])
    assert all(item.answer_key.correct_gap_answers == () for item in exam.items)
    assert len(exam.items) == 7
    assert len(exam.warnings) == len(parse_result.warnings)
    assert len(exam.manual_follow_ups) == 7
    assert all(item.embedded_assets == () for item in exam.items)


def test_dxe_embedded_assets_map_to_ir() -> None:
    payload = json.loads(_EMBEDDED_IMAGE_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["bodyHTML"] = (
        '<p><img data-image-id="0" /></p><p><img data-image-id="0" /></p>'
    )
    parse_result = DigiExamDxeParser(
        image_decodability=PillowEmbeddedImageDecodability()
    ).parse_payload(payload, filename=_EMBEDDED_IMAGE_DXE.name)

    exam = build_digiexam_intermediate_exam(parse_result)
    item = exam.items[0]
    asset = item.embedded_assets[0]

    assert exam.schema_version == DIGIEXAM_IR_SCHEMA_VERSION
    assert len(item.embedded_assets) == 1
    assert item.prompt_html is not None
    assert 'data-image-id="0"' in item.prompt_html
    assert [reference.reference_order for reference in item.embedded_asset_references] == [1, 2]
    assert asset.source_image_index == 0
    assert asset.sha256
    assert asset.media_type == "image/png"
    assert base64.b64decode(asset.content_base64, validate=True)
    assert asset.byte_length > 0
    assert asset.width_px == 1
    assert asset.height_px == 1
    assert len(item.embedded_asset_references) == 2


def test_blocked_parser_output_remains_blocked_in_ir() -> None:
    payload = json.loads(_DXE.read_text(encoding="utf-8"))
    payload["exams"][0]["questions"][0]["type"] = 99
    parse_result = DigiExamDxeParser(
        image_decodability=PillowEmbeddedImageDecodability()
    ).parse_payload(payload, filename="unknown-type.dxe")

    exam = build_digiexam_intermediate_exam(parse_result)

    assert exam.parse_status == DigiExamParseStatus.BLOCKED
    assert exam.renderer_ready is False
    assert DigiExamIrManualFollowUpReason.UNSUPPORTED_ITEM_TYPE in {
        follow_up.reason for follow_up in exam.manual_follow_ups
    }
    assert DigiExamIrManualFollowUpReason.PARSER_WARNING_BLOCKS_RENDERING in {
        follow_up.reason for follow_up in exam.manual_follow_ups
    }
