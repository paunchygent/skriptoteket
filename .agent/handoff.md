# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-03
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: ST-14-01/14-02 done; ST-14-09 done; ST-14-10 done

## Current Session (2026-01-03)

- ST-14-12: sandbox debug panel + copy bundles shipped (helper + tests + UI wiring).
  - Helper: `frontend/apps/skriptoteket/src/composables/editor/sandboxDebugHelpers.ts`
  - Tests: `frontend/apps/skriptoteket/src/composables/editor/sandboxDebugHelpers.spec.ts`
  - UI: `frontend/apps/skriptoteket/src/components/editor/SandboxRunnerActions.vue`
- Older session history moved to `.agent/readme-first.md` (links only) + `docs/`.

## Verification

- Frontend tests: `pdm run fe-test` (pass)
- Frontend lint: `pdm run fe-lint` (pass)
- Frontend typecheck: `pdm run fe-type-check` (pass)
- Live check (dev): `pdm run dev` (running) + `pdm run fe-dev` (running)
- Live check (dev): `curl -sSf http://127.0.0.1:5173/ | head -n 5` (SPA HTML served)
- Live check (Playwright, escalated): `pdm run python - <<'PY'` (login via bootstrap superuser, open editor, run sandbox, verify Debug panel + copy JSON/text)

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development
pdm run dev                 # Backend 127.0.0.1:8000
pdm run fe-dev              # SPA 127.0.0.1:5173

# Quality gates
pdm run format
pdm run lint
pdm run typecheck
pdm run test

# Playwright
pdm run ui-editor-smoke
```

## Known Issues / Risks

- Playwright Chromium may require escalated permissions on macOS (MachPort permission errors); CodeMirror lint tooltip action buttons can be flaky to click in Playwright—use a DOM-evaluate click helper.
- AI inference: llama-server (:8082) + Tabby (:8083) running on hemma; see GPU/Tabby runbooks if services need restart.
- Prompt budgeting is a conservative char→token approximation; rare over-budget cases can still happen and return empty completion/suggestion (see `docs/reference/reports/ref-ai-edit-suggestions-kb-context-budget-blocker.md`).
- Dev UI uses Vite proxy to `127.0.0.1:8000` (host backend); check the `pdm run dev` terminal for errors, not `docker logs`, unless the UI is pointed at the container port directly.

## Next Steps

- ST-14-13+ schema editor work (out of scope here) per `docs/backlog/epics/epic-14-admin-tool-authoring.md`.
- Re-run `pdm run fe-build` after recent editor UI changes.
