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
            parse_native_exam_document(b"{}")
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_document_declares_the_current_schema(self) -> None:
        assert make_document(make_free_text_item()).schema_version == "native_exam_document_v11"

    def test_saved_v1_payload_reports_an_outdated_schema(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v1"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED

    def test_saved_v6_payload_reports_an_outdated_schema(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v6"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED

    def test_saved_v8_payload_reports_an_outdated_schema(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v8"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED

    def test_saved_v9_payload_without_leftover_points_text_reports_an_outdated_schema(
        self,
    ) -> None:
        document = make_document(
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
        )
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v9"
        for item in payload["items"]:
            del item["leftover_points_text"]

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED
        assert exc_info.value.details == {"schema_version": "native_exam_document_v9"}

    def test_leftover_points_text_round_trips(self) -> None:
        document = make_document(
            make_free_text_item(sequence=1, item_id="item_001").model_copy(
                update={"leftover_points_text": "(3 poäng)"}
            ),
            make_free_text_item(sequence=2, item_id="item_002"),
        )

        parsed = parse_native_exam_document(native_exam_document_json_bytes(document))

        assert parsed == document
        assert parsed.items[0].leftover_points_text == "(3 poäng)"
        assert parsed.items[1].leftover_points_text is None

    def test_saved_v10_payload_without_conflicting_source_points_reports_an_outdated_schema(
        self,
    ) -> None:
        document = make_document(
            make_free_text_item(sequence=1, item_id="item_001"),
            make_free_text_item(sequence=2, item_id="item_002"),
        )
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v10"
        for item in payload["items"]:
            del item["conflicting_source_points"]

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED
        assert exc_info.value.details == {"schema_version": "native_exam_document_v10"}

    def test_conflicting_source_points_round_trip(self) -> None:
        document = make_document(
            make_free_text_item(sequence=1, item_id="item_001").model_copy(
                update={"source_points": None, "conflicting_source_points": (4, 5)}
            ),
            make_free_text_item(sequence=2, item_id="item_002"),
        )

        parsed = parse_native_exam_document(native_exam_document_json_bytes(document))

        assert parsed == document
        assert parsed.items[0].conflicting_source_points == (4, 5)
        assert parsed.items[0].source_points is None
        assert parsed.items[1].conflicting_source_points == ()

    def test_missing_schema_version_stays_a_validation_error(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        del payload["schema_version"]

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_v11_header_with_dismissed_mark_is_refused(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        assert isinstance(payload["header"], dict)
        payload["header"]["printed_total_dismissed"] = True

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_source_points_round_trip(self) -> None:
        item = make_free_text_item().model_copy(update={"points": 2, "source_points": 3})
        document = make_document(item)

        parsed = parse_native_exam_document(native_exam_document_json_bytes(document))

        assert parsed == document
        assert parsed.items[0].points == 2
        assert parsed.items[0].source_points == 3

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


class TestOutdatedSchemaMapping:
    def test_outdated_schema_maps_to_422(self) -> None:
        from skriptoteket.web.error_mapping import error_to_status

        assert error_to_status(ErrorCode.DOCUMENT_SCHEMA_OUTDATED) == 422


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
        with pytest.raises(ValidationError, match="import origin requires"):
            NativeExamDocumentOrigin(kind="docx_import")


class TestApiOutputSchema:
    def test_output_schemas_require_the_new_frontend_fields(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="serialization")
        item_schema = NativeExamItem.model_json_schema(mode="serialization")

        assert "automatic_values" in gap_schema.get("required", ())
        assert "facit_text" in item_schema.get("required", ())
        assert "tick_points" in item_schema.get("required", ())
        assert "criteria" in item_schema.get("required", ())

    def test_input_schemas_keep_the_defaults_optional(self) -> None:
        gap_schema = NativeGap.model_json_schema(mode="validation")
        item_schema = NativeExamItem.model_json_schema(mode="validation")

        assert "automatic_values" not in gap_schema.get("required", ())
        assert "facit_text" not in item_schema.get("required", ())
        assert "tick_points" not in item_schema.get("required", ())
        assert "criteria" not in item_schema.get("required", ())


class TestUntrustedDecodeContainment:
    def test_huge_integer_in_document_is_a_validation_error(self) -> None:
        payload = b'{"schema_version": "native_exam_document_v11", "probe": ' + b"9" * 5000 + b"}"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(payload)

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_unknown_decode_error_is_a_validation_error(
        self, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _UnexpectedDecodeError(Exception):
            pass

        def _raise_unexpected(payload: object) -> object:
            raise _UnexpectedDecodeError("injected decode failure")

        monkeypatch.setattr(json, "loads", _raise_unexpected)

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(b"{}")

        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR

    def test_keyboard_interrupt_propagates(self, monkeypatch: pytest.MonkeyPatch) -> None:
        def _raise_interrupted(payload: object) -> object:
            raise KeyboardInterrupt

        monkeypatch.setattr(json, "loads", _raise_interrupted)

        with pytest.raises(KeyboardInterrupt):
            parse_native_exam_document(b"{}")

    def test_outdated_document_keeps_code_and_details(self) -> None:
        document = make_document(make_free_text_item())
        payload = json.loads(native_exam_document_json_bytes(document))
        payload["schema_version"] = "native_exam_document_v9"

        with pytest.raises(DomainError) as exc_info:
            parse_native_exam_document(json.dumps(payload).encode("utf-8"))

        assert exc_info.value.code is ErrorCode.DOCUMENT_SCHEMA_OUTDATED
        assert exc_info.value.details == {"schema_version": "native_exam_document_v9"}
