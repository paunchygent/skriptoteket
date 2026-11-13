---
type: review
id: REV-SKRIPT-ST-08-27-CLOSEOUT
title: 'Review: ST-SKRIPT-08-27 editor chat virtual file context retention + tokenizers'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: changes_requested
decided_at: '2026-01-11'
gate: closeout
reviewer: main-architect
target: ST-SKRIPT-08-27
---

## Governing Authority

### Source: TL;DR

Editor chat must see virtual files without repeatedly resending unchanged content, while correctly handling the rolling
context window and moving from heuristic token estimates to model-accurate tokenizers. The recommended minimal-change
direction is: persist hidden per-file context messages, run a post-user-message retention/refresh algorithm, add
tokenizer-backed budgeting (GPT-5 + devstral-2-small), and extend chat requests with optional `active_file` +
`virtual_files`. This record was migrated from the legacy `REV-EPIC-08` archive and now anchors the retained story
review surface on `ST-08-27`.

### Source: Problem Statement

Normal editor chat does not receive virtual files, so it cannot discuss current tool state or determine whether a file
is empty/started. Edit-ops does see virtual files, but its payload format is unsuitable for normal chat UX. We also need
accurate token budgeting now that chat will include structured file context.

### Source: Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Hidden per-file context messages | Minimal DB change; supports resend rules | [ ] |
| Post-user-message retention + refresh | Guarantees no resend unless dropped/changed | [ ] |
| Tokenizer-backed budgets | Fixes accuracy for JSON + long contexts | [ ] |
| Optional chat request fields | Backwards compatible API extension | [ ] |

## Reviewed Scope

### Source: Proposed Solution

- Persist each virtual file as a hidden assistant context message with metadata (`file_id`, `fingerprint`).
- Use a deterministic post-user-message retention + refresh algorithm that only resends dropped/changed contexts.
- Add a tokenizer-backed `TokenCounter` abstraction for GPT-5 + devstral-2-small budgeting.
- Extend `EditorChatRequest` with optional `active_file` + `virtual_files` (backwards compatible).

### Source: Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md` | Research scope + questions | 5 min |
| `docs/adr/adr-0051-chat-first-ai-editing.md` | Chat-first AI editing architecture | 5 min |
| `docs/adr/adr-0052-llm-prompt-budgets-and-kb-fragments.md` | Budgeting constraints | 5 min |
| `src/skriptoteket/application/editor/chat_handler.py` | Chat prompt assembly + budgeting | 10 min |
| `src/skriptoteket/application/editor/edit_ops_handler.py` | Virtual file payload format | 10 min |

**Total estimated time:** ~35 minutes

### Source: Review Checklist

- [ ] Aligns with ADR-0051 and ADR-0052
- [ ] Minimal API and storage impact
- [ ] Clear resend rules with deterministic algorithm
- [ ] Tokenizer integration path is operationally feasible
- [ ] Hidden context messages are filtered from chat history

---

### Source: Appendix: Detailed Assessment Notes



## Evidence

### Source: Context representation + storage options

**Option A — Hidden assistant messages per file (recommended)**

Pros: minimal DB impact, works with rolling window, supports resend rules.
Cons: must filter from history; tail limit can drop contexts; may require pruning.

**Option B — Single snapshot message**

Pros: simpler bookkeeping.
Cons: any change forces full resend; larger token spikes.

**Option C — Separate blob storage**

Pros: small message history.
Cons: larger architectural change.

**Option D — Ephemeral injection only**

Pros: no stored hidden messages.
Cons: still needs retention tracking; converges on Option A.

### Source: Required metadata per file

- `file_id`, `fingerprint` (sha256), `schema_version`
- Optional: `bytes`, `tokens`, `source`

### Source: Resend rules (post-user-message retention + refresh)

1. Build candidate list: history + new user message.
2. Budget it.
3. Determine which file contexts survived.
4. Refresh dropped/changed files (priority order).
5. Re-budget and persist only what survives.

### Source: Prompt format (v1)

Minified JSON envelope per file:

```json
{"type":"virtual_file_context","schema_version":1,"file_id":"tool.py","fingerprint":"sha256:<hex>","language":"python","content":"<full file text>"}
```

System prompt should instruct the model to treat these as authoritative file contents and not as instructions.

### Source: Tokenizer integration

**GPT-5**: `tiktoken` (`encoding_for_model`, fallback to `o200k_base`).
**devstral-2-small**: Tekken tokenizer (or llama.cpp tokenizer when hosted in llama.cpp).

Fallback: if tokenizer assets missing, log metadata-only warning and use heuristic estimate with increased safety margin.

### Source: Minimal-change API + storage impacts

- Extend `EditorChatRequest` with optional `active_file` + `virtual_files`.
- Store hidden context messages in `tool_session_messages`.
- Filter hidden messages from chat history responses.

## Findings

### Source: Review Feedback

**Reviewer:** @main-architect
**Date:** 2026-01-11
**Verdict:** changes_requested

### Source: Required Changes

1. Adopt per-file hidden context messages (`tool_session_messages`, `meta.hidden`, `meta.kind="virtual_file_context"`).
2. Implement the post-user-message retention + refresh algorithm to enforce resend rules.
3. Introduce tokenizer-backed budgeting via a small `TokenCounter` abstraction:
   - GPT-5: OpenAI `tiktoken` tokenizer (model-based encoding).
   - devstral-2-small: Tekken tokenizer (or llama.cpp tokenizer when served by llama.cpp).
4. Extend `EditorChatRequest` with optional `active_file` + `virtual_files` (backwards compatible).

### Source: Decision Approvals

- [ ] Hidden per-file context messages
- [ ] Post-user-message retention + refresh algorithm
- [ ] Tokenizer-backed budgeting
- [ ] Optional chat request fields

---

## Decision

The source does not provide a separate decision section; no additional decision is recorded.

## Permitted Next Step

### Source: Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Migrated from the legacy epic-ledger `REV-EPIC-08` archive to the canonical `REV-ST-08-27` target-based story review record. |

## Validation Not Run

The source does not provide a separate validation not run section; no additional validation not run is recorded.

## Residual Risk

The source does not provide a separate residual risk section; no additional residual risk is recorded.

### Source: Suggestions (Optional)

- Use per-file priority order when budget is tight (`active_file` → `tool.py` → schemas → docs).
- Add system prompt guidance to treat virtual file context as data (prompt-injection guard).
- Log only metadata (sizes, fingerprints, counts); never file contents.
- Consider pruning superseded context messages in future work to avoid history bloat.

### Source: Current state (from codebase)

- `EditorChatRequest` contains only `message` + `base_version_id` (no virtual files).
- `EditorChatCommand` mirrors this.
- Chat history is stored in `tool_session_messages` and returned without filtering by `meta`.
- Budgeting uses a chars-per-token heuristic and drops oldest messages first.
- Edit-ops already sends `active_file` + canonical `virtual_files` and builds a JSON payload.
