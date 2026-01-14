---
type: pr
id: PR-0029
title: "Editor AI UX copy + prompt/template polish + smooth typing"
status: done
owners: "agents"
created: 2026-01-14
updated: 2026-01-14
stories: []
tags: ["frontend", "backend", "editor", "ai", "ux", "prompts"]
links: ["EPIC-08", "PR-0028", "PR-0030"]
acceptance_criteria:
  - "Tom chatt visar: 'Beskriv vad du vill ha hjälp med. När du är redo att ändra något väljer du \"Edit\".'"
  - "Chat-input placeholder är exakt: 'Fråga mig vad du vill'."
  - "Systemprompter (chat + edit + completion) nämner inte interna termer som 'Contract v2'."
  - "\"Skapa nytt skript\"-mallen visar korrekt inputs/outputs/next_actions/state enligt gällande UI payload."
  - "Chat + Edit-svar känns mjukt 'skrivna' (jämn reveal + subtil fade-in) utan batchiga hopp."
  - "Verifiering körd och loggad i `.agent/handoff.md` inkl. Playwright artifacts under `.artifacts/`."
---

## Problem

Editor-AI upplevs fortfarande som lite “intern” (copy + prompt-terminologi) och streaming kan kännas batchig när
upstream skickar större chunks. “Skapa nytt skript”-mallen behöver också visa den faktiska formen för uppföljning via
`next_actions`/`SKRIPTOTEKET_ACTION`.

Relaterat arbete finns i `docs/backlog/prs/pr-0028-editor-focus-mode-and-ai-drawer-density.md`.

## Goal

- Tydlig, konkret Swedish UX-copy i chat empty-state och chat-input.
- Prompt-texter som instruerar via konkreta format och exempel (utan interna versionsnamn).
- Startmall som demonstrerar korrekt I/O + `next_actions`/`state`.
- “Smooth typing” i UI via frontend progressive reveal (Option B), både för chat-stream och edit-ops.

## Non-goals

- Ändra backend flush-thresholds eller SSE-protokollet.
- Ändra editorflöden för save/publish/review.
- Större prompt-omskrivning eller kontraktsre-design (endast terminologi + små guard rails).

## Implementation plan

1) UX copy
- Uppdatera tom chatt-intro (assistant empty-state).
- Uppdatera chat textarea placeholder i chat-läget.

2) Template/prompt polish
- Uppdatera startmallen så den visar både första körning (`SKRIPTOTEKET_INPUTS`) och uppföljning
  (`SKRIPTOTEKET_ACTION`) med ett fungerande `next_actions`-exempel.
- Ta bort interna referenser till “Contract v2” från systemprompter, men behåll samma placeholder-innehåll och
  constraints i sak.

3) Smooth typing (frontend progressive reveal)
- Rendera assistant text med jämn reveal-hastighet och subtil fade-in för ny text.
- Gäller både SSE-chat (delta) och edit-ops (assistentmeddelande i en klump).

## Files touched

- Frontend: `frontend/apps/skriptoteket/src/components/editor/ChatMessageList.vue`,
  `frontend/apps/skriptoteket/src/components/editor/ChatComposer.vue`,
  `frontend/apps/skriptoteket/src/components/editor/ChatMessageContent.vue`,
  `frontend/apps/skriptoteket/src/components/editor/ScriptEditorAiPanel.vue`,
  `frontend/apps/skriptoteket/src/composables/editor/chat/editorChatReducer.ts`,
  `frontend/apps/skriptoteket/src/composables/editor/chat/editorChatTypes.ts`
- Backend: `src/skriptoteket/web/editor_support.py`,
  `src/skriptoteket/application/editor/prompt_fragments.py`,
  `src/skriptoteket/application/editor/system_prompts/editor_chat_v1.txt`,
  `src/skriptoteket/application/editor/system_prompts/editor_chat_ops_v1.txt`,
  `src/skriptoteket/application/editor/system_prompts/inline_completion_v1.txt`
- Verification: `scripts/playwright_ui_editor_smoke.py`

## Test plan

- FE: `pdm run fe-type-check`, `pdm run fe-test`
- Visual: `BASE_URL=http://localhost:5173 pdm run ui-editor-smoke` (sparar screenshots under `.artifacts/ui-editor-smoke/`)

## Rollback plan

- Revertera ändringar i frontend/back-end prompts + mall. Inga migrations eller dataändringar.
