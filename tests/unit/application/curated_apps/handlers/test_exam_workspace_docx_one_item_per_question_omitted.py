"""A question the reply omits becomes one source review item (TASK-SKRIPT-39-04-12 C3).

Without an entry, each of the question's chunks would be its own review item and its printed
points would be shared out among them; a question the reply lists only as metadata is
likewise omitted, never placed as title or instruction text.
"""

import pytest
from pydantic import JsonValue

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_admission import (
    admit_batch,
)
from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_state import (
    NO_ITEM_REASON,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import (
    NativeExamDocument,
)
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeParseOrigin,
)
from tests.unit.application.curated_apps.handlers.exam_workspace_docx_one_item_test_support import (
    _OTHER,
    _QUESTION,
    _is_source_review,
    _item,
    _paragraph_texts,
    _state,
    _texts,
)

pytestmark = pytest.mark.unit

_VERB = (
    ("paragraph", "Uppgift 2: Förklara vad som kännetecknar ett verb. (2 p)"),
    ("paragraph", "Ge två exempel på verb."),
)


def test_a_question_the_reply_omits_becomes_one_source_review_item():
    # Without an entry, each of the question's four chunks would be its own review item and
    # its printed 4 p would be shared out among them.
    state = _state(_OTHER, _QUESTION)

    admit_batch(
        {"items": [_item(["body:0001"], "Förklara vad ett predikat är.", "Uppgift 1.2")]}, state
    )
    document = state.result().document

    converted, omitted = document.items
    assert converted.review.parse_origin is NativeParseOrigin.LLM_PARSED
    assert _is_source_review(omitted, NO_ITEM_REASON)
    assert _texts(omitted) == [
        "Uppgift 1.1: Subjekt",
        "Stryk under subjektet i varje mening.",
        "1. Hunden skäller på brevbäraren.",
        "2. I morgon reser min syster till Malmö.",
    ]
    assert omitted.points == 4
    assert omitted.source_anchor == "body:0002"
    # D12/D1: the labelled source text stays in the chunks; only the body label left.
    assert state.chunk_by_anchor["body:0002"].text == "Uppgift 1.1: Subjekt (4 p)"


@pytest.mark.parametrize("role", ["instruction", "title"])
@pytest.mark.parametrize("alone", [False, True], ids=["after_q1", "alone"])
def test_a_question_the_reply_lists_as_metadata_becomes_one_source_review_item(
    role: str, alone: bool
):
    # Review-1 F4: no item holds q2 although no chunk of it stays unclaimed.
    state = _state(_VERB) if alone else _state(_OTHER, _VERB)
    own: list[JsonValue] = [
        chunk.anchor for chunk in state.chunks if chunk.text in {t for _, t in _VERB}
    ]
    metadata: dict[str, JsonValue] = {"text": " ".join(t for _, t in _VERB), "source_anchors": own}
    content: dict[str, JsonValue] = {
        "items": [] if alone else [_item(["body:0001"], "Förklara vad ett predikat är.", "1.2")]
    }
    if role == "title":
        content["title"] = metadata
    else:
        content["instructions"] = [metadata]

    admit_batch(content, state)
    result = state.result()
    document = NativeExamDocument.model_validate(result.document.model_dump())

    assert len(document.items) == (1 if alone else 2)
    omitted = document.items[-1]
    assert _is_source_review(omitted, NO_ITEM_REASON)
    assert _texts(omitted) == [
        "Uppgift 2: Förklara vad som kännetecknar ett verb.",
        "Ge två exempel på verb.",
    ]
    assert omitted.source_anchor == own[0]
    # D12/D1: the labelled source text stays in the chunks; only the body label left.
    first_anchor = own[0]
    assert isinstance(first_anchor, str)
    assert (
        state.chunk_by_anchor[first_anchor].text
        == "Uppgift 2: Förklara vad som kännetecknar ett verb. (2 p)"
    )
    placed = _paragraph_texts(document.instructions) + [
        text for parent in document.parents for text in _paragraph_texts(parent.instruction)
    ]
    assert not [text for text in placed for _, own_text in _VERB if own_text in text]
    assert not [own_text for _, own_text in _VERB if own_text in document.title]
