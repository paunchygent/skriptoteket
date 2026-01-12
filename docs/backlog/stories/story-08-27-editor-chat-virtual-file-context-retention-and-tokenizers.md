---
type: story
id: ST-08-27
title: "Research: editor chat virtual file context retention + tokenizer budgets"
status: ready
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
epic: "EPIC-08"
acceptance_criteria:
  - "Given the need for editor chat to see virtual files without resending unchanged context, when research completes, then a documented recommendation exists for context representation, resend rules, and prompt structure."
  - "Given the requirement to decide tokenization accuracy, when research completes, then GPT-5 and devstral-2-small tokenization approaches are compared and a recommended integration path is documented."
  - "Given the existing editor chat/edit-ops architecture, when research completes, then the minimal-change API and storage impacts are identified with explicit tradeoffs and risks."
dependencies:
  - "ST-08-23"
  - "ADR-0051"
  - "ADR-0052"
ui_impact: "No (research only)"
data_impact: "No (research only)"
---

## Context

Editor chat currently does not receive virtual files, while edit-ops does. The next phase must:
- Allow normal chat to see virtual files.
- Avoid resending unchanged virtual files if they are already in the active model context.
- Determine if a virtual file was dropped by the rolling context window (post-user message).
- Replace heuristic token budgeting with accurate tokenizers (GPT-5 + devstral-2-small).
- Start with per-file hidden context messages (Option A) behind a protocol so a future
  swap to blob-backed storage (Option C) is straightforward if storage growth becomes
  a concern.

This story is a research task to answer the design questions before ADRs, stories, and PRs.

## Research questions (design + open questions)

### Context representation + storage
- How should virtual file context be represented in the LLM message list?
  - Dedicated hidden assistant messages?
  - Tool/session messages with metadata only and filtered from UI history?
  - A single snapshot message vs per-file context messages?
- How do we persist context messages in `tool_session_messages` without exposing them in chat history?
- What metadata is required to detect file identity + freshness (file_id, fingerprint, version, etc.)?

### Resend rules + rolling context window
- How do we determine whether a virtual file is still in the active context **after** the user message is added?
- What algorithm guarantees:
  1) no resend when unchanged and still present,
  2) resend when dropped by budget,
  3) resend when file changed?
- Should resend be per-file priority (active file → tool.py → others), and what are the fallback rules if budget is tight?

### Prompt format
- What exact JSON payload format should be used for virtual file context messages?
- Should the chat system prompt be updated to interpret context messages explicitly?
- How do we prevent drift between edit-ops payload format and chat payload format?

### Tokenizer integration
- Which tokenizer implementation should we use for GPT-5 (OpenAI tokenizer)?
- Which tokenizer implementation should we use for devstral-2-small (llama.cpp/llama tokenizer vs sentencepiece)?
- Where should tokenizer assets live (repo vs server), and how are they configured per model?
- What is the fallback when tokenizer assets are missing or mismatched?

### API + minimal-change architecture
- What minimal API changes are required in `EditorChatRequest` (optional `virtual_files`, `active_file`)?
- How do we keep these changes backward compatible?
- How can we reuse existing prompt budgeting logic without duplicating logic across chat + edit-ops?

### Observability + safety
- What metadata can be logged safely (sizes, counts, fingerprints) without leaking content?
- How do we test/verify that resending logic is working (unit + integration)?

## Deliverables

- Research report in `docs/reference/reports/` with:
  - Options + tradeoffs for context storage and resend logic.
  - Recommended algorithm for post-user-message context retention + resend.
  - Tokenizer options and recommended implementation (GPT-5 + devstral-2-small).
  - Minimal-change API proposal aligned to current architecture.
- Draft ADRs (titles + decision summaries) for:
  - Editor chat virtual file context handling.
  - Tokenizer-backed prompt budgeting.
