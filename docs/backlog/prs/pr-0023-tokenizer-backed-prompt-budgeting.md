---
type: pr
id: PR-0023
title: "Tokenizer-backed prompt budgeting (GPT-5 + devstral)"
status: ready
owners: "agents"
created: 2026-01-11
updated: 2026-01-11
stories:
  - "ST-08-27"
tags: ["backend", "ai", "infra"]
acceptance_criteria:
  - "Chat/edit-ops/completions budgeting uses a TokenCounter abstraction with GPT-5 + devstral implementations."
  - "Tokenizer assets are configurable via env and missing assets fall back to heuristic estimation with warnings."
  - "Budgeting behavior remains deterministic and metadata-only logging is preserved."
---

## Problem

Prompt budgeting currently uses a chars-per-token heuristic. With structured virtual file contexts and longer
messages, this becomes inaccurate and can cause over-budget failures or underutilized contexts.

## Goal

- Replace heuristic token estimation with tokenizer-backed counting for GPT-5 and devstral-2-small.
- Keep the change isolated behind a `TokenCounter` abstraction so budgeting logic stays clean.

## Non-goals

- Provider routing/failover changes.
- Adding new models beyond GPT-5 + devstral-2-small.
- UI changes.

## Implementation plan

1. Introduce `TokenCounter` abstraction and wire it into prompt budgeting helpers.
2. GPT-5: use `tiktoken` (`encoding_for_model`, fallback to `o200k_base`).
3. devstral-2-small: use Tekken tokenizer assets (or llama.cpp tokenizer when served via llama.cpp).
4. Add config/env for tokenizer selection + asset paths.
5. Add fallback logic: missing assets -> heuristic estimate + increased safety margin + metadata-only warnings.
6. Update chat/edit-ops/completions to use the new token counter consistently.

## Test plan

- Unit tests for TokenCounter implementations (GPT-5 + devstral).
- Budgeting tests verifying counts and overflow behavior.
- Integration test ensuring missing assets fall back gracefully.

## Rollback plan

Revert the PR; fallback keeps heuristic estimation intact.

## References

- Review: `docs/backlog/reviews/review-epic-08-editor-chat-virtual-files-context.md`
- Story: `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- ADR: `docs/adr/adr-0055-tokenizer-backed-prompt-budgeting.md`
- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`
