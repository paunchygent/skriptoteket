from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from skriptoteket.application.editor.prompt_budget import apply_chat_ops_budget
from skriptoteket.config import Settings
from skriptoteket.protocols.llm import ChatMessage, ChatOpsBudget, EditOpsCommand, VirtualFileId
from skriptoteket.protocols.token_counter import TokenCounterProtocol

from .constants import VIRTUAL_FILE_IDS


def fingerprint_text(text: str) -> str:
    return "sha256:" + hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_base_fingerprints(*, virtual_files: dict[VirtualFileId, str]) -> dict[VirtualFileId, str]:
    return {file_id: fingerprint_text(virtual_files[file_id]) for file_id in VIRTUAL_FILE_IDS}


def build_base_hashes(*, virtual_files: dict[VirtualFileId, str]) -> dict[VirtualFileId, str]:
    return {
        file_id: fingerprint_text(f"{file_id}\u0000{virtual_files[file_id]}")
        for file_id in VIRTUAL_FILE_IDS
    }


def build_base_hash(*, virtual_files: dict[VirtualFileId, str]) -> str:
    payload = "\u0000".join(
        [f"{file_id}\u0000{virtual_files[file_id]}" for file_id in VIRTUAL_FILE_IDS]
    )
    return fingerprint_text(payload)


def build_user_payload(*, command: EditOpsCommand) -> str:
    virtual_files = {file_id: command.virtual_files[file_id] for file_id in VIRTUAL_FILE_IDS}
    payload: dict[str, object] = {
        "message": command.message,
        "active_file": command.active_file,
        "virtual_files": virtual_files,
    }
    if command.selection is not None:
        payload["selection"] = {"from": command.selection.start, "to": command.selection.end}
    if command.cursor is not None:
        payload["cursor"] = {"pos": command.cursor.pos}
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class BudgetPreflightResult:
    messages: list[ChatMessage]
    fits: bool
    prompt_messages_count: int


@dataclass(frozen=True, slots=True)
class OverBudgetMetrics:
    system_prompt_tokens: int
    user_payload_tokens: int
    prompt_budget_tokens: int
    available_history_tokens: int


def apply_budget_preflight(
    *,
    settings: Settings,
    system_prompt: str,
    messages: list[ChatMessage],
    user_payload: str,
    budget: ChatOpsBudget,
    token_counter: TokenCounterProtocol,
) -> BudgetPreflightResult:
    _, budgeted_messages, fits = apply_chat_ops_budget(
        system_prompt=system_prompt,
        messages=messages,
        user_payload=user_payload,
        context_window_tokens=budget.context_window_tokens,
        max_output_tokens=budget.max_output_tokens,
        safety_margin_tokens=settings.LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS,
        system_prompt_max_tokens=settings.LLM_CHAT_OPS_SYSTEM_PROMPT_MAX_TOKENS,
        token_counter=token_counter,
    )
    prompt_messages_count = len(budgeted_messages) + 1
    return BudgetPreflightResult(
        messages=budgeted_messages,
        fits=fits,
        prompt_messages_count=prompt_messages_count,
    )


def build_over_budget_metrics(
    *,
    settings: Settings,
    system_prompt: str,
    user_payload: str,
    budget: ChatOpsBudget,
    token_counter: TokenCounterProtocol,
) -> OverBudgetMetrics:
    system_prompt_tokens = token_counter.count_system_prompt(content=system_prompt)
    user_payload_tokens = token_counter.count_chat_message(role="user", content=user_payload)
    prompt_budget_tokens = (
        budget.context_window_tokens
        - budget.max_output_tokens
        - settings.LLM_CHAT_OPS_CONTEXT_SAFETY_MARGIN_TOKENS
    )
    available_history_tokens = prompt_budget_tokens - system_prompt_tokens - user_payload_tokens
    return OverBudgetMetrics(
        system_prompt_tokens=system_prompt_tokens,
        user_payload_tokens=user_payload_tokens,
        prompt_budget_tokens=prompt_budget_tokens,
        available_history_tokens=available_history_tokens,
    )
