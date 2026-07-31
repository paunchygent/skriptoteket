---
type: task
id: TASK-SKRIPT-08-27-03
title: Tokenizer-backed prompt budgeting (GPT-5 + devstral)
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-08-27
task_kind: story
acceptance_criteria:
- Chat/edit-ops/completions budgeting uses a TokenCounter abstraction with GPT-5 +
  devstral implementations.
- Token counting accounts for chat template/role overhead (devstral in particular),
  not just raw message content.
- Tokenizer assets are configurable via env and missing assets fall back to heuristic
  estimation with warnings.
- All estimate_text_tokens call sites are replaced or removed in favor of TokenCounter
  (prompt_budget, prompt_composer, chat handler prechecks).
- Budgeting behavior remains deterministic and metadata-only logging is preserved.
---

## Context


Prompt budgeting currently uses a chars-per-token heuristic. With structured virtual file contexts and longer
messages, this becomes inaccurate and can cause over-budget failures or underutilized contexts.

## Decision And Assumption Ledger

| source | semantic | carried_forward | Source material is retained in the sections above. | source |

## Story Contract Slice


- Replace heuristic token estimation with tokenizer-backed counting for GPT-5 and devstral-2-small.
- Keep the change isolated behind a `TokenCounter` abstraction so budgeting logic stays clean.

## Contract Inputs

No separate contract inputs is stated in the source.

## Plan


1. Introduce `TokenCounter` abstraction and wire it into prompt budgeting helpers.
2. GPT-5: use `tiktoken` (`encoding_for_model`, fallback to `o200k_base`).
3. devstral-2-small: use Tekken tokenizer assets (or llama.cpp tokenizer when served via llama.cpp).
4. Add config/env for tokenizer selection + asset paths.
5. Add fallback logic: missing assets -> heuristic estimate + increased safety margin + metadata-only warnings.
6. Replace all estimate_text_tokens call sites (prompt_budget, prompt_composer, chat handler prechecks) with TokenCounter.
7. Ensure devstral token counting includes chat template overhead (rendered template or explicit per-message overhead).

## Implementation Steps

No separate implementation steps is stated in the source.

## Proof


- Unit tests for TokenCounter implementations (GPT-5 + devstral).
- Budgeting tests verifying counts and overflow behavior.
- Integration test ensuring missing assets fall back gracefully.
- Tests that devstral counting includes template overhead (fixture assets or deterministic overhead constant).

## Validation

No separate validation is stated in the source.

## Stop Conditions


Revert the PR; fallback keeps heuristic estimation intact.

## Lessons Learned

No separate lessons learned is stated in the source.

## Notes

No separate notes is stated in the source.

### Source: Non-goals


- Provider routing/failover changes.
- Adding new models beyond GPT-5 + devstral-2-small.
- UI changes.

### Source: References


- Review: `docs/backlog/reviews/review-st-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- Story: `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
- ADR: `docs/adr/adr-0055-tokenizer-backed-prompt-budgeting.md`
- Epic: `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`

## Plan Document Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.

## Implementation Review

No review evidence is recorded in this migration candidate; the frontmatter gate remains authoritative.
