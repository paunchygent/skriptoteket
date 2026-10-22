"""Edit-ops handler tests.

Purpose:
    Verify the single chat-ops provider call through the LLM provider door:
    caller identity, turn persistence, door limit refusal, and the outcome of
    each provider failure kind.
"""

from __future__ import annotations

import json

import pytest

from skriptoteket.application.editor.edit_ops.constants import INVALID_OPS_ERROR, MESSAGE_TOO_LONG
from skriptoteket.domain.errors import DomainError, ErrorCode
from skriptoteket.domain.identity.models import Role
from skriptoteket.domain.llm_door import (
    AiDailyLimit,
    AiDailyLimitReached,
    AiDoorBusy,
    ai_try_again_note,
)
from skriptoteket.protocols.llm import (
    EditOpsCommand,
    EditOpsCursor,
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

_PATCH_RESPONSE = {
    "assistant_message": "OK",
    "ops": [
        {
            "op": "patch",
            "target_file": "tool.py",
            "patch_lines": [
                "diff --git a/tool.py b/tool.py",
                "--- a/tool.py",
                "+++ b/tool.py",
                "@@ -1,1 +1,1 @@",
                "-print('hej')",
                "+print('hello')",
            ],
        }
    ],
}


def _command(harness: EditOpsHarness) -> EditOpsCommand:
    return EditOpsCommand(
        tool_id=harness.tool_id,
        message="Hej",
        active_file="tool.py",
        cursor=EditOpsCursor(pos=0),
        virtual_files=virtual_files(),
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_returns_disabled_without_writing_turn() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(settings=make_settings(LLM_CHAT_OPS_ENABLED=False), actor_id=actor.id)

    result = await harness.handler.handle(actor=actor, command=_command(harness))

    assert result.enabled is False
    harness.provider.complete_chat_ops.assert_not_called()
    harness.turns.create_turn.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_calls_provider_with_the_actors_door_caller_and_finalizes_turn() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(settings=make_settings(LLM_CHAT_OPS_ENABLED=True), actor_id=actor.id)
    harness.provider.complete_chat_ops.return_value = LLMChatOpsResponse(
        content=json.dumps(_PATCH_RESPONSE, ensure_ascii=False),
        finish_reason=None,
        raw_payload={"choices": []},
    )

    result = await harness.handler.handle(actor=actor, command=_command(harness))

    assert result.enabled is True
    assert result.assistant_message == "OK"
    assert len(result.ops) == 1

    harness.provider.complete_chat_ops.assert_awaited_once()
    caller = harness.provider.complete_chat_ops.await_args.kwargs["caller"]
    assert caller.user_id == actor.id

    harness.turns.create_turn.assert_awaited_once()
    assert harness.messages.create_message.await_count == 2
    harness.turns.update_status.assert_awaited_once()
    update_kwargs = harness.turns.update_status.await_args.kwargs
    assert update_kwargs["turn_id"] == harness.turn_id
    assert update_kwargs["status"] == "complete"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("limit", "note"),
    [
        (AiDailyLimit.POOL, "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."),
        (
            AiDailyLimit.USER_SHARE,
            "Du har nått din gräns för AI-hjälp i dag. Försök igen i morgon.",
        ),
        (AiDailyLimit.USD_CEILING, "Appens AI-hjälp har nått dagens gräns. Försök igen i morgon."),
    ],
)
async def test_edit_ops_door_limit_refusal_raises_limit_error_and_fails_the_turn(
    limit: AiDailyLimit, note: str
) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(settings=make_settings(LLM_CHAT_OPS_ENABLED=True), actor_id=actor.id)
    harness.provider.complete_chat_ops.side_effect = AiDailyLimitReached(limit=limit)

    with pytest.raises(DomainError) as raised:
        await harness.handler.handle(actor=actor, command=_command(harness))

    assert raised.value.code is ErrorCode.AI_DAILY_LIMIT_REACHED
    assert raised.value.message == note
    assert raised.value.details == {"limit": limit.value}

    harness.turns.update_status.assert_awaited_once()
    update_kwargs = harness.turns.update_status.await_args.kwargs
    assert update_kwargs["turn_id"] == harness.turn_id
    assert update_kwargs["status"] == "failed"
    assert update_kwargs["failure_outcome"] == "ai_daily_limit_reached"
    content_kwargs = harness.messages.update_message_content_if_pending_turn.await_args.kwargs
    assert content_kwargs["content"] == note
    assert harness.guard.released == harness.guard.acquired
    assert len(harness.guard.released) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_busy_door_raises_try_again_and_fails_the_turn() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(settings=make_settings(LLM_CHAT_OPS_ENABLED=True), actor_id=actor.id)
    harness.provider.complete_chat_ops.side_effect = AiDoorBusy(retry_after_seconds=3)

    with pytest.raises(DomainError) as raised:
        await harness.handler.handle(actor=actor, command=_command(harness))

    assert raised.value.code is ErrorCode.AI_TRY_AGAIN
    assert raised.value.message == ai_try_again_note()
    assert raised.value.details == {"retry_after_seconds": 3}
    update_kwargs = harness.turns.update_status.await_args.kwargs
    assert update_kwargs["status"] == "failed"
    assert update_kwargs["failure_outcome"] == "ai_door_busy"
    content_kwargs = harness.messages.update_message_content_if_pending_turn.await_args.kwargs
    assert content_kwargs["content"] == ai_try_again_note()
    assert harness.guard.released == harness.guard.acquired
    assert len(harness.guard.released) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_context_window_exceeded_gives_the_over_budget_answer() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(
        settings=make_settings(LLM_CHAT_OPS_ENABLED=True, LLM_CAPTURE_ON_ERROR_ENABLED=True),
        actor_id=actor.id,
    )
    harness.provider.complete_chat_ops.side_effect = EditorLlmProviderError(
        kind="context_window_exceeded", status_code=400, detail="too long"
    )

    result = await harness.handler.handle(actor=actor, command=_command(harness))

    assert result.enabled is True
    assert result.assistant_message == MESSAGE_TOO_LONG
    assert result.ops == []
    assert result.eval_meta is not None
    assert result.eval_meta.outcome == "over_budget"
    update_kwargs = harness.turns.update_status.await_args.kwargs
    assert update_kwargs["status"] == "failed"
    assert update_kwargs["failure_outcome"] == "over_budget"


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["timeout", "request_failed", "http_status", "invalid_response"])
async def test_edit_ops_other_provider_failures_give_the_invalid_ops_answer(kind: str) -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(settings=make_settings(LLM_CHAT_OPS_ENABLED=True), actor_id=actor.id)
    harness.provider.complete_chat_ops.side_effect = EditorLlmProviderError(
        kind=kind,  # type: ignore[arg-type]
        status_code=502 if kind == "http_status" else None,
    )

    result = await harness.handler.handle(actor=actor, command=_command(harness))

    assert result.enabled is True
    assert result.assistant_message == INVALID_OPS_ERROR
    assert result.ops == []
    assert result.eval_meta is not None
    assert result.eval_meta.outcome == "error"
    assert harness.turns.update_status.await_args.kwargs["status"] == "failed"
    assert len(harness.guard.released) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_edit_ops_over_budget_prompt_never_calls_the_provider() -> None:
    actor = make_user(role=Role.CONTRIBUTOR)
    harness = make_harness(
        settings=make_settings(
            LLM_CHAT_OPS_ENABLED=True,
            LLM_CHAT_OPS_CONTEXT_WINDOW_TOKENS=64,
            LLM_CHAT_OPS_MAX_TOKENS=16,
            LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS=8,
        ),
        actor_id=actor.id,
    )

    result = await harness.handler.handle(actor=actor, command=_command(harness))

    assert result.assistant_message == MESSAGE_TOO_LONG
    harness.provider.complete_chat_ops.assert_not_called()
    harness.turns.create_turn.assert_not_called()


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_leaves_role_admission_to_the_web_gate() -> None:
    actor = make_user(role=Role.USER)
    harness = make_harness(settings=make_settings(LLM_CHAT_OPS_ENABLED=True), actor_id=actor.id)
    harness.provider.complete_chat_ops.return_value = LLMChatOpsResponse(
        content=json.dumps(_PATCH_RESPONSE, ensure_ascii=False),
        finish_reason=None,
        raw_payload={"choices": []},
    )

    result = await harness.handler.handle(actor=actor, command=_command(harness))

    assert result.enabled is True
    assert result.assistant_message == "OK"
    harness.provider.complete_chat_ops.assert_awaited_once()
    harness.turns.create_turn.assert_awaited_once()
