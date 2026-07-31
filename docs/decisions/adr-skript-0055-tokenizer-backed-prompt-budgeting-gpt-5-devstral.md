---
type: adr
id: ADR-SKRIPT-0055
title: Tokenizer-backed prompt budgeting (GPT-5 + devstral)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
deciders:
- user-lead
retired_ids:
- ADR-0055
---

## Context

Source: `docs/adr/adr-0055-tokenizer-backed-prompt-budgeting.md`. Tokenizer-backed prompt budgeting (GPT-5 + devstral).

Prompt budgeting currently uses a chars-per-token heuristic, which becomes inaccurate when we add structured virtual file context to editor chat. Research is captured in: - `docs/reference/reports/ref-editor-chat-virtual-file-context-tokenizers-2026-01-11.md` - Introduce a small `TokenCounter` abstraction used by chat, edit-ops, and completions budgeting. - GPT-5 uses OpenAI `tiktoken` (`encoding_for_model`, fallback to `o200k_base`). - devstral-2-small uses Tekken tokenizer assets (or llama.cpp tokenizer when served via llama.cpp runtime). - Tokenizer assets are provided via deploy-time paths; missing assets fall back to heuristic estimates with increased safety margin and metadata-only log

## Decision

The migrated ADR preserves the source decision and its accepted boundary. Source evidence is retained below.

## Non-Decisions

No new decision, implementation authority, or terminal-state promotion is introduced by this migration.

## Consequences

### Source evidence

### Context

Prompt budgeting currently uses a chars-per-token heuristic, which becomes inaccurate when we add structured virtual
file context to editor chat. Research is captured in:

- `docs/reference/reports/ref-editor-chat-virtual-file-context-tokenizers-2026-01-11.md`

### Decision

- Introduce a small `TokenCounter` abstraction used by chat, edit-ops, and completions budgeting.
- GPT-5 uses OpenAI `tiktoken` (`encoding_for_model`, fallback to `o200k_base`).
- devstral-2-small uses Tekken tokenizer assets (or llama.cpp tokenizer when served via llama.cpp runtime).
- Tokenizer assets are provided via deploy-time paths; missing assets fall back to heuristic estimates with
  increased safety margin and metadata-only logging.

### Consequences

- Budgeting becomes model-accurate, reducing prompt overflow errors.
- Adds operational requirements for tokenizer assets.
- Slightly more complex infra wiring, but isolated behind a protocol for clean reuse.
