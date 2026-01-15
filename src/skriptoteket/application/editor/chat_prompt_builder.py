from __future__ import annotations

import json

from skriptoteket.application.editor.chat_shared import (
    CHAT_USER_PAYLOAD_KIND,
    CHAT_USER_PAYLOAD_SCHEMA_VERSION,
    MESSAGE_TOO_LONG,
    VIRTUAL_FILE_IDS,
)
from skriptoteket.application.editor.prompt_budget import apply_chat_budget, apply_chat_ops_budget
from skriptoteket.config import Settings
from skriptoteket.domain.errors import validation_error
from skriptoteket.protocols.editor_chat import EditorChatPromptBuilderProtocol
from skriptoteket.protocols.llm import ChatBudget, ChatMessage, LLMChatRequest, VirtualFileId
from skriptoteket.protocols.token_counter import TokenCounterProtocol


def _virtual_file_priority_high_to_low(*, active_file: VirtualFileId) -> list[VirtualFileId]:
    ordered: list[VirtualFileId] = []
    seen: set[VirtualFileId] = set()

    def add(file_id: VirtualFileId) -> None:
        if file_id in seen:
            return
        seen.add(file_id)
        ordered.append(file_id)

    add(active_file)
    for file_id in VIRTUAL_FILE_IDS:
        add(file_id)
    return ordered


class SettingsBasedEditorChatPromptBuilder(EditorChatPromptBuilderProtocol):
    def __init__(self, *, settings: Settings) -> None:
        self._settings = settings

    def plan_max_user_message_tokens(
        self, *, system_prompt: str, token_counter: TokenCounterProtocol, budget: ChatBudget
    ) -> int | None:
        prompt_budget_tokens = (
            budget.context_window_tokens
            - budget.max_output_tokens
            - self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS
        )
        if prompt_budget_tokens <= 0:
            return None

        system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
        available_message_tokens = prompt_budget_tokens - system_prompt_tokens
        if available_message_tokens <= 0:
            return None

        max_user_message_tokens = available_message_tokens - 1
        if max_user_message_tokens <= 0:
            return None

        return max_user_message_tokens

    def validate_plain_user_message(
        self,
        *,
        message: str,
        max_user_message_tokens: int,
        token_counter: TokenCounterProtocol,
    ) -> None:
        if token_counter.count_chat_message(role="user", content=message) > max_user_message_tokens:
            raise validation_error(MESSAGE_TOO_LONG)

    def _build_chat_user_payload(
        self,
        *,
        message: str,
        active_file: VirtualFileId,
        virtual_files: dict[VirtualFileId, str],
        max_payload_tokens: int,
        token_counter: TokenCounterProtocol,
    ) -> str:
        ordered_files = _virtual_file_priority_high_to_low(active_file=active_file)
        included: list[VirtualFileId] = [active_file]
        for file_id in ordered_files:
            if file_id == active_file:
                continue
            included.append(file_id)

        while True:
            selected_files = {file_id: virtual_files.get(file_id, "") for file_id in included}
            omitted = [file_id for file_id in ordered_files if file_id not in included]
            payload_obj: dict[str, object] = {
                "kind": CHAT_USER_PAYLOAD_KIND,
                "schema_version": CHAT_USER_PAYLOAD_SCHEMA_VERSION,
                "message": message,
                "active_file": active_file,
                "virtual_files": selected_files,
                "omitted_virtual_file_ids": omitted,
            }
            payload = json.dumps(payload_obj, ensure_ascii=False, separators=(",", ":"))
            payload_tokens = token_counter.count_chat_message(role="user", content=payload)
            if payload_tokens <= max_payload_tokens:
                return payload

            if len(included) <= 1:
                raise validation_error(MESSAGE_TOO_LONG)
            included.pop()  # drop lowest priority until it fits

    def build_user_payload_message(
        self,
        *,
        message: str,
        active_file: VirtualFileId | None,
        virtual_files: dict[VirtualFileId, str],
        max_user_message_tokens: int,
        token_counter: TokenCounterProtocol,
    ) -> ChatMessage:
        effective_active_file = active_file or "tool.py"
        if effective_active_file not in VIRTUAL_FILE_IDS:
            effective_active_file = "tool.py"

        payload = self._build_chat_user_payload(
            message=message,
            active_file=effective_active_file,
            virtual_files=virtual_files,
            max_payload_tokens=max_user_message_tokens,
            token_counter=token_counter,
        )
        return ChatMessage(role="user", content=payload)

    def build_llm_request(
        self,
        *,
        system_prompt: str,
        existing_messages: list[ChatMessage],
        message: str,
        user_payload_message: ChatMessage | None,
        token_counter: TokenCounterProtocol,
        budget: ChatBudget,
    ) -> LLMChatRequest:
        if user_payload_message is None:
            proposed = [*existing_messages, ChatMessage(role="user", content=message)]
            _, budgeted = apply_chat_budget(
                system_prompt=system_prompt,
                messages=proposed,
                context_window_tokens=budget.context_window_tokens,
                max_output_tokens=budget.max_output_tokens,
                safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
                system_prompt_max_tokens=self._settings.LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS,
                token_counter=token_counter,
            )
            if not budgeted:
                raise validation_error(MESSAGE_TOO_LONG)
            return LLMChatRequest(messages=budgeted)

        _, budgeted, fits = apply_chat_ops_budget(
            system_prompt=system_prompt,
            messages=existing_messages,
            user_payload=user_payload_message.content,
            context_window_tokens=budget.context_window_tokens,
            max_output_tokens=budget.max_output_tokens,
            safety_margin_tokens=self._settings.LLM_CHAT_CONTEXT_SAFETY_MARGIN_TOKENS,
            system_prompt_max_tokens=self._settings.LLM_CHAT_SYSTEM_PROMPT_MAX_TOKENS,
            token_counter=token_counter,
        )
        if not fits:
            raise validation_error(MESSAGE_TOO_LONG)
        return LLMChatRequest(messages=[*budgeted, user_payload_message])
