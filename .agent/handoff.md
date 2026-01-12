# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-12
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: recent — ST-08-24 done; ST-08-28 done (history: `.agent/readme-first.md`)

## Current Session (2026-01-12)

- Added ADR + story for settings suggestions from tool runs: `docs/adr/adr-0057-settings-suggestions-from-tool-runs.md`, `docs/backlog/stories/story-14-34-settings-suggestions-from-tool-runs.md`, linked in `docs/index.md` + `docs/backlog/epics/epic-14-admin-tool-authoring.md` (docs-only).
- Drafted docs for script bank curation + group generator tool: `docs/adr/adr-0056-script-bank-seed-profiles.md`, `docs/backlog/stories/story-14-33-script-bank-curation-and-group-generator.md`, `docs/backlog/prs/pr-0025-script-bank-curation-and-group-generator.md`; linked in `docs/index.md` + `docs/backlog/epics/epic-14-admin-tool-authoring.md`. Verification: not run (docs-only).
- Handoff compression: moved detailed “shipped AI editor work + verification recipes” to `.agent/readme-first.md`.
- Contract decision prep (EPIC-14 / ST-14-19): recorded decision to move action payload transport to `SKRIPTOTEKET_ACTION` (ADRs updated) + added PR doc `docs/backlog/prs/pr-0024-action-payload-skriptoteket-action-docs-prompt-alignment.md`; `pdm run docs-validate` OK.
- Baseline: `docs/adr/adr-0051-chat-first-ai-editing.md` is `accepted`; EPIC-08 summary refreshed in `docs/backlog/epics/epic-08-contextual-help-and-onboarding.md`.
- Platform-only AI debug capture (Option A): `LLM_CAPTURE_ON_ERROR_ENABLED` + captures under `ARTIFACTS_ROOT/llm-captures/` (access: `docs/runbooks/runbook-observability-logging.md`).
- ST-08-27 (pending): virtual file context retention + tokenizer budgets:
  - `docs/backlog/stories/story-08-27-editor-chat-virtual-file-context-retention-and-tokenizers.md`
  - `docs/backlog/reviews/review-epic-08-editor-chat-virtual-files-context.md`
  - `docs/adr/adr-0054-editor-chat-virtual-file-context.md`, `docs/adr/adr-0055-tokenizer-backed-prompt-budgeting.md`
  - `docs/reference/reports/ref-editor-chat-virtual-file-context-tokenizers-2026-01-11.md`
  - `docs/backlog/prs/pr-0022-editor-chat-virtual-file-context-retention.md`, `docs/backlog/prs/pr-0023-tokenizer-backed-prompt-budgeting.md`
- ADR-0054 decision locked: virtual file context messages stay `role="assistant"` and budgeting preserves assistant context envelopes (`virtual_file_context`).
- Quick verification: `pdm run docs-validate`; `pdm run pytest tests/unit/application/test_editor_edit_ops_handler.py tests/unit/application/test_editor_edit_ops_preview_handler.py -q`.

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000

# Quality gates
pdm run format
pdm run lint
pdm run typecheck
pdm run test
```

## Known Issues / Risks

- Streaming cancellation: client disconnect cancels upstream best-effort; `done.reason="cancelled"` may not be observed client-side if the connection is already closed.
- Prompt budgeting is a conservative char→token approximation; rare over-budget cases can still happen (ST-08-27 targets this).
- If `LLM_CHAT_ENABLED=false` (default) or chat is misconfigured, SSE returns a single `done` event with the Swedish “not available” message.

## Next Steps

- ST-08-27: complete review decisions + pick implementation direction (context retention strategy + tokenizers).
- ST-14-19: implement `SKRIPTOTEKET_ACTION` + runner toolkit (no shims); update script bank + tests that currently rely on `action.json`.
- Decide whether to keep or remove any story-specific Playwright scripts (prefer using `pdm run ui-editor-smoke`).
- Parallel refactors (optional): PR-0019 (backend LLM hotspots) + PR-0020 (frontend AI hotspots).
