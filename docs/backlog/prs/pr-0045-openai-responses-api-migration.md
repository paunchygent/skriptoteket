---
type: pr
id: PR-0045
title: "AI: migrate OpenAI providers to Responses API"
status: done
owners: "agents"
created: 2026-01-18
updated: 2026-01-18
stories:
  - "ST-08-31"
tags: ["backend", "ai", "openai"]
acceptance_criteria:
  - "OpenAI-backed providers use `/v1/responses` with payloads aligned to the OpenAI Responses API reference."
  - "GPT-5-specific parameters (e.g., `text.verbosity`, `reasoning.effort`) are used per the GPT-5 cookbook guidance."
  - "Prompt caching follows the prompt-caching guide (prefix ordering, `prompt_cache_key`, 1024-token threshold)."
  - "Local llama-server providers continue using the Chat Completions-compatible path."
  - "Unit tests cover payload translation for inline completions, chat, and chat-ops."
---

## Problem

We currently target the Chat Completions API for OpenAI. GPT-5 guidance and prompt-caching
best practices now favor the Responses API, especially for reasoning workflows and cache
efficiency. We need to migrate OpenAI providers without breaking local llama-backed
providers or changing UI behavior.

## Goal

- Migrate OpenAI providers to the Responses API.
- Align request payloads with GPT-5 guidance (verbosity, reasoning effort, tool/grammar usage).
- Preserve prompt caching behavior and improve cache utilization.

## Non-goals

- Changing prompts or UX behavior.
- Rewriting local llama-server integrations.
- Adding new observability dashboards (see PR-0044).

## Implementation plan

1. Add a Responses API provider implementation for OpenAI (inline completions, chat, chat-ops).
2. Map existing settings to Responses API fields:
   - `text.verbosity` for output length control (GPT-5 cookbook).
   - `reasoning.effort` for low/medium/high reasoning effort.
3. Preserve prompt caching behavior:
   - Keep `prompt_cache_key`.
   - Ensure prompt prefixes are stable and >=1024 tokens where caching is expected.
4. Maintain Chat Completions path for local llama-server.
5. Add unit tests for payload translation and capability gating per model.
6. Update docs to reference the new runbook as the source of truth.

## Test plan

- Unit tests for Responses API payload translation.
- Manual: run `/api/v1/editor/completions` with OpenAI base URL and confirm 200 responses.
- Manual: verify `cached_tokens` appears for long prompts (>=1024 tokens).
- Manual: verify local llama-server requests still work.

## Rollback plan

- Revert provider wiring to Chat Completions for OpenAI and keep the Responses provider code behind a feature flag.
