---
type: pr
id: PR-0030
title: "Editor chat streaming: reactive messages + typing status"
status: in_progress
owners: "agents"
created: 2026-01-14
updated: 2026-01-14
stories: []
tags: ["frontend", "editor", "ai", "ux"]
links: ["PR-0029"]
acceptance_criteria:
  - "Assistant streaming updates the UI on each delta (no 'wait until done' behavior)."
  - "Inline status uses 'Tänker...' until the first visible batch is rendered, then 'Skriver...'."
  - "Chat composer status uses the same thinking/writing semantics (no 'AI skriver...')."
  - "Typing reveal is driven by a composable-level controller (steady pace + subtle fade per chunk)."
  - "Verification is recorded in `.agent/handoff.md` including Playwright artifacts under `.artifacts/`."
---

## Problem

After PR-0029 introduced frontend progressive reveal, chat output can still feel like it is held back until the answer is
complete. In addition, the inline “Skriver...” indicator can get stuck due to message object identity / reactivity issues.

We also want the process wording to be more accurate:

- Show **“Tänker...”** while the assistant is working but no output has been shown yet.
- Switch to **“Skriver...”** only once the first *visible* batch is rendered.

## Goal

- Make chat message objects reactive at creation time, so delta/appended updates always re-render.
- Move the reveal controller into the composable (separate raw content from visible content) to decouple UX from backend
  chunking.
- Update chat UI status labels to use “Tänker...” / “Skriver...” (and avoid “AI skriver...”).

## Non-goals

- Changing backend SSE protocol / flush thresholds.
- Redesigning the chat drawer layout or editor workflows.

## Implementation plan

1) **Reactive messages (root fix)**
- Wrap new/mapped `EditorChatMessage` objects with Vue `reactive()` and ensure we only mutate the proxied versions.

2) **Composable reveal controller**
- Track `content` (raw) + `visibleContent` (rendered) and advance `visibleContent` in small batches at a stable pace.
- Keep `visibleContent` as a strict prefix of `content` (single source of truth for raw).

3) **Thinking vs writing status**
- Inline per-message: `Tänker...` until `visibleContent.length > 0`, then `Skriver...` while streaming.
- Composer row: same semantics (computed from the active streaming message; fallback to “Tänker...” before the message exists).

4) **Fade-in rendering**
- Keep `ChatMessageContent.vue` as a dumb renderer that fades in the latest appended chunk.

## Test plan

- FE: `pdm run fe-type-check`, `pdm run fe-test`
- Visual: `BASE_URL=http://localhost:5173 pdm run ui-editor-smoke`

## Rollback plan

- Revert PR-0030 changes. No migrations or data changes.
