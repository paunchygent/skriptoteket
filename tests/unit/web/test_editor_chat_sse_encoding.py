from __future__ import annotations

import json
from uuid import uuid4

import pytest

from skriptoteket.protocols.llm import EditorChatMetaData, EditorChatMetaEvent
from skriptoteket.web.api.v1.editor import chat as chat_api


@pytest.mark.unit
def test_encode_sse_event_serializes_uuid_fields() -> None:
    correlation_id = uuid4()
    turn_id = uuid4()
    assistant_message_id = uuid4()

    event = EditorChatMetaEvent(
        data=EditorChatMetaData(
            correlation_id=correlation_id,
            turn_id=turn_id,
            assistant_message_id=assistant_message_id,
        )
    )

    payload = chat_api._encode_sse_event(event).decode("utf-8")
    assert payload.startswith("event: meta\ndata: ")

    json_line = payload.split("data: ", 1)[1].split("\n", 1)[0]
    parsed = json.loads(json_line)
    assert parsed["correlation_id"] == str(correlation_id)
    assert parsed["turn_id"] == str(turn_id)
    assert parsed["assistant_message_id"] == str(assistant_message_id)
