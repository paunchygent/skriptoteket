"""Pictures reach the converter as bounded asset IDs, never binary payloads."""

import json
from uuid import uuid4

from skriptoteket.application.curated_apps.handlers.exam_workspace_docx_build_rounds import (
    _model_chunk,
    build_batch_request,
)
from skriptoteket.domain.curated_apps.exam_conversion.digiexam_answer_key_llm_contracts import (
    StructuredLLMEndpointKind,
    StructuredLLMProviderProfile,
)
from skriptoteket.domain.curated_apps.exam_workspace.docx_chunks import DocxChunk, DocxImage
from skriptoteket.domain.curated_apps.exam_workspace.native_exam_document import NativeExamItemKind


def test_model_chunk_keeps_two_pictures_between_their_original_text_runs() -> None:
    first = DocxImage(b"first secret image bytes", "image/png", offset=2, marked_offset=9)
    second = DocxImage(b"second image", "image/jpeg", offset=2, marked_offset=9)
    chunk = DocxChunk("body:0002", "paragraph", "ABCD", "<i>AB</i>CD", (first, second))
    result = _model_chunk(chunk)
    assert result["text"] == (
        f'<i>AB</i><image asset_id="{first.asset_id}"/><image asset_id="{second.asset_id}"/>CD'
    )
    assert "secret" not in result["text"]


def test_request_schema_offers_only_owned_picture_ids_not_context_pictures() -> None:
    image = DocxImage(b"owned", "image/png")
    context_image = DocxImage(b"context-only", "image/png")
    request = build_batch_request(
        job_id=uuid4(),
        request_id="picture-question",
        pending=(DocxChunk("body:0002", "drawing", "", "", (image,)),),
        context=(DocxChunk("body:0001", "drawing", "", "", (context_image,)),),
        kinds=frozenset({NativeExamItemKind.FREE_TEXT}),
        profile=StructuredLLMProviderProfile(
            provider_id="test",
            model="test",
            endpoint_kind=StructuredLLMEndpointKind.RESPONSES,
            is_remote=True,
            context_window_tokens=32_768,
            max_output_tokens=4_096,
        ),
    )
    schema = json.dumps(request.output_spec.json_schema)
    assert image.asset_id in schema
    assert context_image.asset_id not in schema
    assert json.loads(request.user_payload)["chunks"][0]["text"] == (
        f'<image asset_id="{image.asset_id}"/>'
    )
