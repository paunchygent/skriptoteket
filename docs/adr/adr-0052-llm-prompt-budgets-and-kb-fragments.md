---
type: adr
id: ADR-0052
title: "LLM prompt budgeting + KB fragments for AI editor features"
status: accepted
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-31
updated: 2026-01-04
links: ["EPIC-08", "ADR-0043", "ADR-0051", "ST-08-18", "ST-08-23", "ST-08-21",
"REF-ai-completion-architecture"]
---

## Context

ST-08-14 (inline completions) and ST-08-16 (edit suggestions) rely on
injecting a knowledge base
into the system prompt. The existing KB (`docs/reference/ref-ai-script-
generation-kb.md`) is
human-readable and large (~900 LoC). When used verbatim, prompts exceed the
local model context
window (llama.cpp default 4096), producing upstream 400 errors and backend
500s.

We control the backend, so prompt size and truncation must be enforced
deterministically and safely.
We also need a stable, reviewable prompt surface that does not drift from
Contract v2 or runner constraints.

Update (2026-01-02): The roadmap includes chat-first AI editing (ADR-0051),
which introduces:

- multi-turn conversation context (bounded history / summary)
- multi-document authoring context (virtual files: tool.py, entrypoint.txt,
  settings_schema.json, input_schema.json, usage_instructions.md)
- longer outputs (structured edit operations + explanations)

These increase the importance of explicit context-window coordination and
output token budgets.

## Decision

1. **Use repo-owned system prompt templates + code-owned fragments**
   Compose system prompts from:
   - repo-owned templates (selected by template ID)
   - code-owned fragments sourced from canonical definitions (Contract v2 +
runner constraints + helpers)

2. **Enforce a context budget in the backend (per capability profile)**
   Budgets MUST be enforced per capability profile, not shared implicitly:
   - inline completions (`LLM_COMPLETION_*`)
   - edit suggestions (`LLM_EDIT_*`)
   - chat streaming (`LLM_CHAT_*`)
   - chat edit ops (`LLM_CHAT_OPS_*`)
   The budget accounting MUST include:
   - system prompt (templates + fragments)
   - instruction
   - selection/cursor context (if applicable)
   - prefix/suffix (if applicable)
   - conversation context (bounded tail and optional bounded summary) for chat
flows
   - virtual file payloads (multiple logical documents) for chat ops
   - expected completion/output tokens
   Truncate deterministically (keep selection intact; trim suffix/prefix
first; reduce conversation tail/summary next; reduce system prompt last if
needed).

3. **Graceful handling of over-budget responses**
   Treat upstream “context too large” responses as non-fatal:
   - Return enabled with empty output/ops as appropriate
   - Log prompt sizing metadata (no code/content)

## Consequences

- System prompts become reviewable, testable repo artifacts, and contract-
  sensitive content is sourced from canonical code.
- Prompt budgets are enforced consistently across providers and model context
  windows.
- Avoids LLM failures that manifest as 500s and improves real-pipeline
  reliability.

## Notes

An LLM-optimized KB reference exists at `docs/reference/ref-ai-script-
generation-kb-llm.md`, but prompt injection uses
the template/fragment system so Contract v2 and runner constraints remain the
single source of truth.
