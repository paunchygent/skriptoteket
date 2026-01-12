---
type: reference
id: REF-editor-chat-virtual-file-context-tokenizers-2026-01-11
title: "Research: Editor chat virtual file context + tokenizer budgeting"
status: active
owners: "agents"
created: 2026-01-11
topic: "editor-ai"
---

## Executive summary

Editor chat currently streams plain chat messages only, while edit-ops receives `active_file` + canonical
`virtual_files`. The next phase should let **normal chat** see virtual files *without* repeatedly resending unchanged
file content, while handling the rolling context window correctly and replacing heuristic token estimation with
model-accurate tokenizers.

**Recommended direction (minimal change, architecture-aligned):**

1. **Represent each virtual file as a hidden, persisted context message** stored in `tool_session_messages` and filtered
   from the chat history API response.
2. **Use a deterministic “post-user-message retention + refresh” algorithm** to resend only dropped/changed files.
3. **Introduce tokenizer-backed budgeting** via a small `TokenCounter` abstraction (GPT-5 + devstral-2-small).
4. **Minimal API addition**: optional `active_file` + `virtual_files` in `EditorChatRequest` (backwards compatible).
5. **Design for refactorability**: place context persistence behind a protocol so a future swap to blob storage is easy.

## Current state (from codebase)

- `EditorChatRequest` includes only `message` + `base_version_id` (no virtual files).
- `EditorChatCommand` mirrors this.
- Chat history is stored in `tool_session_messages` and returned to the UI without filtering by `meta`.
- Budgeting uses `estimate_text_tokens()` (chars-per-token heuristic) with “drop oldest messages first.”
- Edit-ops already sends `active_file` + `virtual_files` and builds a JSON payload.

Key files:

- Chat: `src/skriptoteket/web/api/v1/editor/chat.py`, `src/skriptoteket/application/editor/chat_handler.py`
- Edit-ops: `src/skriptoteket/application/editor/edit_ops_handler.py`
- Budgeting: `src/skriptoteket/application/editor/prompt_budget.py`
- Request models: `src/skriptoteket/web/api/v1/editor/models.py`, `src/skriptoteket/protocols/llm.py`

## Option A vs Option C (deeper comparison)

### Option A — per-file hidden context messages (recommended)

**Representation**
- One hidden assistant message per virtual file.
- Stored in `tool_session_messages` with `meta`:
  - `hidden: true`, `kind: "virtual_file_context"`, `file_id`, `fingerprint` (sha256).

**Duplication size**
- Typical snapshot size (rough, per tool):
  - `tool.py`: 10–30 KB
  - schemas + instructions + entrypoint: 5–15 KB
  - **Total per snapshot**: ~15–45 KB + small JSON overhead.
- If a user edits the tool 10 times: ~150–450 KB per tool per user.
- Even at scale, this is usually within Postgres tolerance, and old contexts are not re-sent to the model (latest-only).

**How to manage growth**
- Prompt assembly only uses the **latest** context per file.
- Optional pruning: delete older context messages per file after writing the latest.
- TTL already removes inactive threads after 30 days.

**Pros**
- Minimal DB/API changes.
- Resend rules are natural: dropped/changed contexts are just missing messages.
- Works with existing chat storage flow.

**Cons**
- Must filter hidden messages out of chat history responses.
- Tail limit can drop contexts early; requires retention+refresh logic.

### Option C — separate blob storage + references

**Representation**
- `tool_session_messages` stores only a reference:
  - `file_id`, `fingerprint`, `blob_ref`.
- File content is stored in a separate table or blob store.

**Pros**
- Keeps message history smaller.
- Allows deduplication by fingerprint.

**Cons**
- Larger architectural change: new table, lifecycle, cleanup, and extra reads.
- More failure modes (missing blobs, GC races).
- Still must load full content into prompts, so runtime budget does not improve.

**Viability**
- Viable, but not minimal. Recommended only if Option A storage growth becomes a concern.

## DDD/CC alignment (refactor-friendly boundary)

To keep future swaps cheap, introduce a narrow **protocol boundary**:

- `VirtualFileContextRepositoryProtocol` (or similar) that the application layer uses for:
  - `list_latest_contexts(...)`
  - `append_context(...)`
  - `prune_contexts(...)` (optional)

Infrastructure can implement this via:
- Option A: `tool_session_messages` (current schema).
- Option C: blob-backed storage in a future phase.

This keeps domain logic stable and ensures Option C can be dropped in later with minimal refactor.

## Resend rules + rolling context window (summary)

**Invariants**
1) No resend when unchanged and still retained.
2) Resend when dropped by budget.
3) Resend when file changed.

**Recommended algorithm (post-user-message retention + refresh)**

1) Build candidate prompt: history + new user message.
2) Apply budget **after** adding the user message.
3) Inspect which file contexts survived.
4) Refresh dropped/changed files in priority order.
5) Re-budget and persist only contexts that survived.

## Prompt format (context envelope)

Recommended JSON envelope per file:

```json
{"type":"virtual_file_context","schema_version":1,"file_id":"tool.py","fingerprint":"sha256:<hex>","language":"python","content":"<full file text>"}
```

Add system prompt guidance: treat these as **data**, not instructions (prompt-injection guard).

## Tokenizer integration (GPT-5 + devstral-2-small)

**GPT-5**
- Use OpenAI `tiktoken` (`encoding_for_model` with fallback to `o200k_base`).

**devstral-2-small**
- Use Tekken tokenizer (or llama.cpp tokenizer if running via llama.cpp runtime).
- Store tokenizer assets as deploy-time artifacts (avoid committing large tokenizer files).

**Fallback**
- If tokenizer assets are missing/mismatched, log metadata-only warnings and fall back to heuristic estimates with a
  larger safety margin.

## Open questions / decision points

- Confirm Option A (hidden per-file messages) as default; Option C as future swap.
- Confirm priority order under tight budgets (active_file → tool.py → schemas → docs).
- Confirm tokenizer asset location and expected runtime for devstral (Tekken vs llama.cpp).

## Next steps (after research approval)

- Draft ADRs:
  - Editor chat virtual file context handling (Option A behind protocol).
  - Tokenizer-backed prompt budgeting (GPT-5 + devstral).
- Define story-level acceptance criteria for implementation (post-research).
