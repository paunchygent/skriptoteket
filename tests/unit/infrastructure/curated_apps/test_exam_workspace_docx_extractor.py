"""Real-fixture tests for the python-docx exam workspace extractor (D1)."""

import hashlib
from pathlib import Path
from uuid import uuid4

import pytest

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamItemKind,
    NativeItemReviewState,
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.infrastructure.curated_apps.apps.conversion_hub import (
    exam_workspace_docx_extractor,
)

PythonDocxExamExtractor = exam_workspace_docx_extractor.PythonDocxExamExtractor

_FIXTURE = Path(
    "tests/fixtures/exam_conversion/real_inputs/grammatik_omprov_examnet_import_med_facit.docx"
)


@pytest.fixture(scope="module")
def fixture_bytes() -> bytes:
    content = _FIXTURE.read_bytes()
    sidecar = _FIXTURE.with_suffix(".docx.sha256").read_text().split()[0]
    assert hashlib.sha256(content).hexdigest() == sidecar
    return content


@pytest.fixture(scope="module")
def extracted(fixture_bytes: bytes):
    return PythonDocxExamExtractor().extract(
        document_id=uuid4(),
        filename=_FIXTURE.name,
        content=fixture_bytes,
    )


class TestRealFixtureExtraction:
    def test_document_header(self, extracted) -> None:
        document = extracted.document
        assert document.title == "Omprov: grammatik och språkstrukturer"
        assert document.instructions == ("Svenska 2", "Total: 38 poäng")
        assert document.origin.kind == "docx_import"
        assert document.origin.source_filename == _FIXTURE.name
        assert extracted.notes == ()

    def test_eight_items_with_declared_points_total(self, extracted) -> None:
        items = extracted.document.items
        assert len(items) == 8
        assert sum(item.points or 0 for item in items) == 38

    def test_item_kind_distribution(self, extracted) -> None:
        kinds = [item.kind for item in extracted.document.items]
        assert kinds.count(NativeExamItemKind.GAP_FILL) == 7
        assert kinds.count(NativeExamItemKind.FREE_TEXT) == 1

    def test_clean_questions_are_review_complete(self, extracted) -> None:
        by_id = {item.item_id: item for item in extracted.document.items}
        for item_id in ("item_002", "item_003", "item_008"):
            assert by_id[item_id].review.state is NativeItemReviewState.REVIEW_COMPLETE, item_id

    def test_ambiguous_questions_require_review(self, extracted) -> None:
        by_id = {item.item_id: item for item in extracted.document.items}
        assert "multiple_answer_labels_detected" in by_id["item_004"].review.reasons
        assert "long_answer_key" in by_id["item_001"].review.reasons
        for item_id in ("item_001", "item_004", "item_005", "item_006", "item_007"):
            assert by_id[item_id].review.state is NativeItemReviewState.REVIEW_REQUIRED, item_id

    def test_frastyp_keys_extracted_exactly(self, extracted) -> None:
        item = extracted.document.item_by_id("item_002")
        assert [gap.accepted_values for gap in item.gaps] == [
            ("NF",),
            ("VF",),
            ("PF",),
            ("PF",),
        ]

    def test_extracted_document_round_trips(self, extracted) -> None:
        payload = native_exam_document_json_bytes(extracted.document)
        assert parse_native_exam_document(payload) == extracted.document


class TestRejection:
    def test_non_docx_bytes_rejected_with_domain_error(self) -> None:
        with pytest.raises(DomainError) as exc_info:
            PythonDocxExamExtractor().extract(
                document_id=uuid4(), filename="prov.docx", content=b"not a docx"
            )
        assert exc_info.value.code is ErrorCode.VALIDATION_ERROR
