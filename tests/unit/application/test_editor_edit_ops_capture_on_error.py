from __future__ import annotations

from contextlib import contextmanager
from uuid import UUID, uuid4

import pytest
from structlog.contextvars import bind_contextvars, clear_contextvars

from skriptoteket.domain.identity.models import Role
from skriptoteket.protocols.llm import (
    EditOpsCommand,
    EditorLlmProviderError,
    LLMChatOpsResponse,
)
from tests.fixtures.identity_fixtures import make_user
from tests.unit.application.edit_ops_harness import (
    EditOpsHarness,
    make_harness,
    make_settings,
    virtual_files,
)


@contextmanager
def _bound_correlation_id(correlation_id: UUID):
    clear_contextvars()
    bind_contextvars(correlation_id=str(correlation_id))
    try:
        yield
    finally:
        clear_contextvars()


def _command(harness: EditOpsHarness) -> EditOpsCommand:
    return EditOpsCommand(
        tool_id=harness.tool_id,
        message="Hej",
        active_file="tool.py",
        selection=None,
        cursor=None,
        virtual_files=virtual_files(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_writes_capture_on_parse_failed_when_enabled() -> None:
    correlation_id = uuid4()
    with _bound_correlation_id(correlation_id):
        actor = make_user(role=Role.CONTRIBUTOR)
        harness = make_harness(
            settings=make_settings(LLM_CHAT_OPS_ENABLED=True, LLM_CAPTURE_ON_ERROR_ENABLED=True),
            actor_id=actor.id,
        )
        harness.provider.complete_chat_ops.return_value = LLMChatOpsResponse(
            content="not-json",
            finish_reason=None,
            raw_payload={"choices": []},
        )

        result = await harness.handler.handle(actor=actor, command=_command(harness))

        assert result.enabled is True
        assert result.ops == []

        harness.messages.update_message_content_if_pending_turn.assert_awaited_once()
        harness.turns.update_status.assert_awaited_once()

        harness.capture_store.write_capture.assert_awaited_once()
        kwargs = harness.capture_store.write_capture.await_args.kwargs
        assert kwargs["kind"] == "chat_ops_response"
        assert kwargs["capture_id"] == correlation_id
        payload = kwargs["payload"]
        assert payload["outcome"] == "parse_failed"
        assert payload["tool_id"] == str(harness.tool_id)
        assert payload["extracted_content"] == "not-json"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_capture_on_http_status_failure_keeps_status_code_and_detail() -> None:
    correlation_id = uuid4()
    with _bound_correlation_id(correlation_id):
        actor = make_user(role=Role.CONTRIBUTOR)
        harness = make_harness(
            settings=make_settings(LLM_CHAT_OPS_ENABLED=True, LLM_CAPTURE_ON_ERROR_ENABLED=True),
            actor_id=actor.id,
        )
        harness.provider.complete_chat_ops.side_effect = EditorLlmProviderError(
            kind="http_status", status_code=502, detail="bad gateway"
        )

        await harness.handler.handle(actor=actor, command=_command(harness))

        harness.capture_store.write_capture.assert_awaited_once()
        payload = harness.capture_store.write_capture.await_args.kwargs["payload"]
        assert payload["outcome"] == "invalid_ops"
        assert payload["upstream_error"] == {
            "error_type": "EditorLlmProviderError",
            "kind": "http_status",
            "status_code": 502,
            "detail": "bad gateway",
        }
        assert "provider" not in payload
        assert "allow_remote_fallback" not in payload
