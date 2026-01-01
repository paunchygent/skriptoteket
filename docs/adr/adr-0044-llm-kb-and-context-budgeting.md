---
type: adr
id: ADR-0044
title: "LLM KB artifact and context budgeting for AI editor features"
status: proposed
owners: "agents"
deciders: ["user-lead"]
created: 2025-12-31
---

## Context

ST-08-14 (inline completions) and ST-08-16 (edit suggestions) rely on injecting a knowledge base
into the system prompt. The existing KB (`docs/reference/ref-ai-script-generation-kb.md`) is
human-readable and large (~900 LoC). When used verbatim, prompts exceed the local model context
window (llama.cpp default 4096), producing upstream 400 errors and backend 500s.

We control the backend, so prompt size and truncation must be enforced deterministically.
We also need a stable artifact that is explicitly authored for LLM consumption.

## Decision (Proposed)

1. **Introduce a dedicated LLM KB artifact**
   Use `docs/reference/ref-ai-script-generation-kb-llm.md` as the **only** KB injected into
   LLM system prompts. Keep it short, rule-focused, and optimized for token budget.

2. **Enforce a context budget in the backend**
   Define a prompt budget that accounts for:
   - system KB
   - instruction
   - selection
   - prefix/suffix
   - expected completion tokens
   Truncate deterministically (keep selection intact; trim prefix/suffix first; reduce KB last).

3. **Graceful handling of over-budget responses**
   Treat upstream “context too large” responses as non-fatal:
   - Return enabled with empty suggestion
   - Log prompt sizing metadata (no code content)

## Consequences

- Requires maintaining **two KBs**:
  - Human KB (full reference, documentation)
  - LLM KB (short, system prompt artifact)
- Adds explicit config for KB path and budget, improving operational control.
- Avoids LLM failures that manifest as 500s and improves real-pipeline reliability.

## Notes

This ADR is **proposed** and must follow the review workflow before implementation changes
that depend on it.
