---
type: story
id: ST-08-31
title: "AI: migrate OpenAI providers to Responses API"
status: ready
owners: "agents"
created: 2026-01-18
epic: "EPIC-08"
acceptance_criteria:
  - "Given OpenAI providers are enabled, when the backend makes requests, then it uses the Responses API (`/v1/responses`) with payloads aligned to the OpenAI Responses API reference."
  - "Given GPT-5 models, when requesting output length control or minimal reasoning, then the backend uses `text.verbosity` and `reasoning.effort` in accordance with the GPT-5 cookbook guidance."
  - "Given prompt caching is enabled, when prompts are >=1024 tokens, then `usage.prompt_tokens_details.cached_tokens` is recorded and used to assess cache efficiency."
  - "Given local llama-server providers, when the backend makes requests, then it continues to use the Chat Completions-compatible path."
---

## Context

OpenAI recommends using the Responses API for GPT-5 models and for reasoning workflows.
Prompt caching behavior and reasoning-item handling are better described in the Responses API
cookbook and guides, so we should align our OpenAI integrations accordingly.

## Notes

- Source of truth for parameters, caching, and best practices:
  `docs/runbooks/runbook-openai-responses-api.md`.
