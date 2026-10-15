"""Unit tests for the source-neutral native exam document (ST-SKRIPT-39-04)."""

import json

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_criteria import (
    NativeExamCriterion,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocumentOrigin,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_values import NativeGap
from skriptoteket.domain.errors import DomainError, ErrorCode
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
    make_gap_fill_item,
    make_single_choice_item,
)


class TestSerializationRoundTrip:
    def test_json_round_trip_preserves_document(self) -> None:
        document = make_document(
            make_gap_fill_item(sequence=1, item_id="item_001"),
            make_single_choice_item(sequence=2, item_id="item_002"),
            make_free_text_item(sequence=3, item_id="item_003"),
        )
        payload = native_exam_document_json_bytes(document)
        assert parse_native_exam_document(payload) == document

    def test_serialization_is_deterministic(self) -> None:
        document = make_document(make_free_text_item())
        assert native_exam_document_json_bytes(document) == native_exam_document_json_bytes(
            document
        )

    def test_invalid_json_raises_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b"not json")
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_invalid_payload_raises_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b'{"schema_version": "native_exam_document_v1"}')
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_document_declares_the_v2_schema(self) -> None:
        assert make_document(make_free_text_item()).schema_version == "native_exam_document_v2"

    def test_saved_v1_payload_has_no_compatibility_reader(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v1"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_round_trip_preserves_facit_text_and_automatic_values(self) -> None:
        document = make_document(
            make_gap_fill_item(
                accepted=("katt",),
                automatic=("kat", "ktat", "kattn", "hund"),
                facit_text="Djuret som eftersöks är en katt.",
            )
        )
        (item,) = document.items

        assert item.facit_text == "Djuret som eftersöks är en katt."
        assert item.gaps[0].automatic_values == ("kat", "ktat", "kattn")
        assert parse_native_exam_document(native_exam_document_json_bytes(document)) == document

    def test_round_trip_preserves_the_criteria_list(self) -> None:
        item = make_free_text_item().model_copy(
            update={
                "points": 3,
                "criteria": (
                    NativeExamCriterion(text="Ett korrekt exempel.", points=2),
                    NativeExamCriterion(text="En korrekt förklaring.", points=1),
                ),
            }
        )
        document = make_document(item)

        parsed = parse_native_exam_document(native_exam_document_json_bytes(document))

        assert parsed == document
        assert parsed.items[0].criteria[1].text == "En korrekt förklaring."


class TestDocumentInvariants:
    def test_sequences_must_be_contiguous(self) -> None:
        with pytest.raises(ValidationError, match="contiguous"):
            make_document(
                make_free_text_item(sequence=1, item_id="item_001"),
                make_free_text_item(sequence=3, item_id="item_002"),
            )

    def test_item_ids_must_be_unique(self) -> None:
        with pytest.raises(ValidationError, match="unique"):
            make_document(
                make_free_text_item(sequence=1, item_id="item_001"),
                make_free_text_item(sequence=2, item_id="item_001"),
            )

    def test_docx_import_origin_requires_source_fields(self) -> None:
        with pytest.raises(ValidationError, match="docx_import origin requires"):
            NativeExamDocumentOrigin(kind="docx_import")


class TestApiOutputSchema:
    def test_output_schemas_require_the_new_frontend_fields(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="serialization")
        item_schema = NativeExamItem.model_json_schema(mode="serialization")

        assert "automatic_values" in gap_schema.get("required", ())
        assert "facit_text" in item_schema.get("required", ())
        assert "criteria" in item_schema.get("required", ())

    def test_input_schemas_keep_the_defaults_optional(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="validation")
        item_schema = NativeExamItem.model_json_schema(mode="validation")

        assert "automatic_values" not in gap_schema.get("required", ())
        assert "facit_text" not in item_schema.get("required", ())
        assert "criteria" not in item_schema.get("required", ())
