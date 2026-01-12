---
type: pr
id: PR-0019
title: "AI: SRP/DI refactor audit follow-ups (LLM hotspots)"
status: ready
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-23"
  - "ST-08-24"
  - "ST-08-25"
  - "ST-08-26"
  - "ST-08-27"
tags: ["backend", "ai", "refactor", "srp", "di"]
links: ["EPIC-08"]
acceptance_criteria:
  - "`src/skriptoteket/infrastructure/llm/openai_provider.py` is split into cohesive modules (per provider type + shared helpers), without changing public behavior."
  - "`src/skriptoteket/application/editor/chat_handler.py` is refactored to separate persistence, budgeting, failover orchestration, and stream event production (Protocol-first DI)."
  - "`src/skriptoteket/application/editor/edit_ops_handler.py` delegates LLM JSON parsing/validation to an injected `EditOpsPayloadParserProtocol` (or equivalent), keeping the handler thin."
  - "GPT-5 detection/capabilities logic is centralized and reused by both OpenAI provider code and the chat-ops budget resolver."
  - "Unit tests + `pdm run lint` + `pdm run typecheck` pass."
---

## Problem

AI/LLM modules have grown quickly during the AI sprint and now mix multiple responsibilities, making them harder to
test, reason about, and evolve safely.

## Goal

- Enforce SRP boundaries in AI/LLM hotspots.
- Keep application handlers thin and protocol-driven (protocol-first DI).
- Centralize model-family capability detection to avoid drift.
- Preserve runtime behavior (refactor only).

## Non-goals

- Adding new provider features (beyond mechanical refactor).
- Changing chat/edit-ops behavior, thread semantics, or UX.
- Expanding failover/routing to additional LLM profiles (outside chat/chat-ops).

## SRP audit (AI sprint hotspots)

- `src/skriptoteket/infrastructure/llm/openai_provider.py`: multiple providers + OpenAI/llama quirks + parsing helpers in one module; candidate split per provider type + shared helpers.
- `src/skriptoteket/application/editor/chat_handler.py`: persistence + budgeting + failover orchestration + stream event production; candidate extraction similar to the budget-resolver refactor (e.g. chat budget resolver / stream orchestrator).
- `src/skriptoteket/application/editor/edit_ops_handler.py`: still mixes orchestration with JSON parsing/validation; candidate extract `EditOpsPayloadParserProtocol` / validator.
- Duped GPT-5 detection in `src/skriptoteket/infrastructure/llm/openai_provider.py` and `src/skriptoteket/infrastructure/llm/chat_ops_budget_resolver.py`; candidate centralize in a small shared infra helper.

### Additional audit notes (optional follow-ups)

- `src/skriptoteket/application/editor/edit_ops_preview_handler.py` is >400 LOC and may warrant a similar “thin handler + extracted services” pass if it continues to grow.

## Implementation plan

1. Centralize model-family capability detection (e.g., `is_gpt5_family_model`) in a shared infra helper module and use it from both the OpenAI provider code and budget resolvers.
2. Split `openai_provider.py` into smaller modules:
   - Keep shared HTTP + parsing helpers in a shared module.
   - Keep provider implementations per profile (completion/chat/chat-ops) in separate modules implementing existing protocols.
3. Refactor `EditorChatHandler`:
   - Extract thread persistence/restore/TTL concerns into a focused component.
   - Extract budget computation into a `ChatBudgetResolverProtocol` (or equivalent).
   - Extract stream orchestration into a component that turns upstream deltas/errors into `EditorChatStreamEvent`.
4. Refactor `EditOpsHandler`:
   - Extract fenced-block/JSON extraction + pydantic validation into an injected parser/validator protocol.
   - Keep `EditOpsHandler` focused on composing prompts, routing providers, and persisting messages.
5. Add/adjust unit tests for each extracted component and ensure DI wiring remains protocol-first.

## Test plan

- `pdm run pytest tests/unit -q`
- `pdm run lint`
- `pdm run typecheck`

## Rollback plan

- Revert the PR; no data migrations are involved.
