"""Contract-first matrix for the stored ``suggested_kind`` and its retry source."""

import random

import pytest
from pydantic import ValidationError

from skriptoteket.domain.curated_apps.exam_workspace.native_exam_change_type import change_item_type
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamDocument
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document_json import (
    native_exam_document_json_bytes,
    parse_native_exam_document,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_item import NativeExamItem
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_retry_records import (
    NativeExamRetryChunk,
    NativeExamRetrySource,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_change_type_test_support import (
    KINDS,
    expected_dropped,
    source_item,
)
from tests.unit.domain.curated_apps.exam_workspace.native_exam_test_builders import (
    make_document,
    make_free_text_item,
)


def _retry_source(label_kind: NativeExamItemKind) -> NativeExamRetrySource:
    return NativeExamRetrySource(
        chunks=(
            NativeExamRetryChunk(
                anchor="body:0001",
                kind="paragraph",
                text="Original question wording",
                marked_text="Original question wording",
                runs=(),
                paragraphs=(),
            ),
        ),
        owned_context_anchors=(),
        key_chunks=(),
        context_chunks=(),
        label_kind=label_kind,
    )


@pytest.mark.parametrize("target", KINDS, ids=lambda kind: kind.value)
@pytest.mark.parametrize(
    ("source", "suggestion"),
    [(source, suggestion) for source in KINDS for suggestion in KINDS if source is not suggestion],
    ids=lambda kind: kind.value,
)
def test_suggestion_is_consumed_only_by_its_target_kind(
    source: NativeExamItemKind,
    suggestion: NativeExamItemKind,
    target: NativeExamItemKind,
) -> None:
    payload = source_item(source).model_dump()
    payload.update(suggested_kind=suggestion, retry_source=_retry_source(suggestion))
    item = NativeExamItem.model_validate(payload)
    sibling_payload = make_free_text_item(sequence=2, item_id="item_002").model_dump()
    sibling_payload.update(
        suggested_kind=NativeExamItemKind.SINGLE_CHOICE,
        retry_source=_retry_source(NativeExamItemKind.SINGLE_CHOICE),
    )
    sibling = NativeExamItem.model_validate(sibling_payload)
    document = make_document(item, sibling)
    before = document.model_dump(mode="json")

    result = change_item_type(
        document, item_id=item.item_id, target_kind=target, rng=random.Random(1)
    )

    changed = result.document.items[0]
    assert changed.kind is target
    assert changed.suggested_kind is (None if target is suggestion else suggestion)
    assert changed.retry_source == item.retry_source
    assert result.document.items[1] == sibling
    assert document.model_dump(mode="json") == before, "Consuming cannot mutate the input"
    assert set(result.dropped_content) == expected_dropped(item, target)
    assert NativeExamDocument.model_validate(result.document.model_dump()) == result.document
    if target is source:
        assert result.document is document, "A no-op must preserve the pending suggestion"


def test_consumed_suggestion_stays_absent_after_an_unrelated_manual_type_change() -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        suggested_kind=NativeExamItemKind.SINGLE_CHOICE,
        retry_source=_retry_source(NativeExamItemKind.SINGLE_CHOICE),
    )
    original = NativeExamItem.model_validate(payload)
    accepted = change_item_type(
        make_document(original),
        item_id=original.item_id,
        target_kind=NativeExamItemKind.SINGLE_CHOICE,
        rng=random.Random(1),
    ).document
    assert accepted.items[0].suggested_kind is None

    manually_changed = change_item_type(
        accepted,
        item_id=original.item_id,
        target_kind=NativeExamItemKind.GAP_FILL,
        rng=random.Random(1),
    ).document

    changed = manually_changed.items[0]
    assert changed.kind is NativeExamItemKind.GAP_FILL
    assert changed.retry_source == original.retry_source
    assert changed.suggested_kind is None
    assert NativeExamDocument.model_validate(manually_changed.model_dump()) == manually_changed


@pytest.mark.parametrize("label_kind", KINDS, ids=lambda kind: kind.value)
def test_missing_suggestion_is_valid_even_when_the_source_label_differs(
    label_kind: NativeExamItemKind,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.pop("suggested_kind")
    payload["retry_source"] = _retry_source(label_kind)

    item = NativeExamItem.model_validate(payload)

    assert item.suggested_kind is None
    assert item.retry_source is not None
    assert item.retry_source.label_kind is label_kind


@pytest.mark.parametrize(
    ("label_kind", "suggestion", "message"),
    [
        (
            NativeExamItemKind.FREE_TEXT,
            NativeExamItemKind.FREE_TEXT,
            "suggested kind must differ from the item's kind",
        ),
        (None, NativeExamItemKind.SINGLE_CHOICE, "suggested kind requires retry source"),
        (
            NativeExamItemKind.GAP_FILL,
            NativeExamItemKind.SINGLE_CHOICE,
            "suggested kind must match the retry source's label kind",
        ),
    ],
    ids=["already-current-kind", "missing-source", "disagrees-with-label"],
)
def test_invalid_suggested_kind_is_rejected(
    label_kind: NativeExamItemKind | None,
    suggestion: NativeExamItemKind,
    message: str,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        suggested_kind=suggestion,
        retry_source=_retry_source(label_kind) if label_kind is not None else None,
    )

    with pytest.raises(ValidationError, match=message):
        NativeExamItem.model_validate(payload)


@pytest.mark.parametrize("suggestion", [None, NativeExamItemKind.SINGLE_CHOICE])
def test_v7_document_round_trip_stores_suggested_kind(
    suggestion: NativeExamItemKind | None,
) -> None:
    payload = make_free_text_item().model_dump()
    payload.update(
        suggested_kind=suggestion,
        retry_source=_retry_source(NativeExamItemKind.SINGLE_CHOICE),
    )
    document = make_document(NativeExamItem.model_validate(payload))

    encoded = native_exam_document_json_bytes(document)
    restored = parse_native_exam_document(encoded)

    assert restored == document
    assert restored.schema_version == "native_exam_document_v11"
    assert restored.items[0].suggested_kind is suggestion
    assert restored.model_dump(mode="json")["items"][0]["suggested_kind"] == (
        suggestion.value if suggestion is not None else None
    )
