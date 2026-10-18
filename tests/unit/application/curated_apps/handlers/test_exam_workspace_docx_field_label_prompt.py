"""A phrase printed after a field label is given material unless the question's instruction
asks the student for it; it stays text (D44).

The live eval run d26-real-1fam-low-27 made the six "Bisats:" clauses of
``svenska_2_grammatik_omprov_variant_1_med_facit`` Fråga 6 gaps and still passed as
reviewed, because that question's instruction asks for the clause's type and clause element,
not the clause itself. The rule reaches the converter as one structural prompt sentence; this
test pins it to the system prompt of the request the provider receives, so a prompt edit
cannot silently drop it.
"""

from uuid import uuid4

import pytest

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    build_batch_request,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_vocabulary import (
    NativeExamItemKind,
)

pytestmark = pytest.mark.unit

_FIELD_LABEL_RULE = (
    "A phrase printed after a field label is given material unless the question's instruction "
    "asks the student for it; it stays text and is never a gap."
)


def _profile() -> StructuredLLMProviderProfile:
    return StructuredLLMProviderProfile(
        provider_id="openai-gpt-5.6-luna",
        model="gpt-5.6-luna",
        endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
        is_remote=True,
        context_window_tokens=32_768,
        max_output_tokens=4_096,
    )


def _squashed(text: str) -> str:
    return " ".join(text.split())


def test_the_converter_system_prompt_carries_the_field_label_rule() -> None:
    request = build_batch_request(
        job_id=uuid4(),
        request_id="w1-01",
        pending=(
            DocxChunk(
                anchor="body:0001",
                kind="paragraph",
                text="a) Jag vet att lektionen börjar klockan tio. Bisats: Typ: Satsdel:",
                marked_text="a) Jag vet att lektionen börjar klockan tio. Bisats: Typ: Satsdel:",
            ),
        ),
        context=(),
        questions=(("body:0001",),),
        kinds=frozenset({NativeExamItemKind.GAP_FILL}),
        profile=_profile(),
    )

    assert _squashed(request.system_prompt).count(_FIELD_LABEL_RULE) == 1
