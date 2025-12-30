# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2025-12-30
- Branch / commit: `main` (`2a04d3d`)
- Current sprint: `SPR-2026-01-05 Tool Editor Vertical Slice` (EPIC-14)
- Production: Full Vue SPA (unchanged)
- Completed: EPIC-14 Admin Tool Authoring (ST-14-01/14-02) done

## Current Session (2025-12-30)

- **AI infrastructure deployed**: llama-server (ROCm) + Tabby on hemma for self-hosted code completion.
  - Model: Qwen3-Coder-30B-A3B (MoE, ~18.5GB VRAM); ADR-0050; runbooks in `docs/runbooks/`.
- EPIC-06 linter (ST-06-10/11/12): lint panel + navigation keymaps live in intelligence (`frontend/apps/skriptoteket/src/composables/editor/skriptoteketLintPanel.ts`, `frontend/apps/skriptoteket/src/composables/editor/skriptoteketIntelligence.ts`); base editor stays generic (`frontend/apps/skriptoteket/src/components/editor/CodeMirrorEditor.vue`).
- ST-06-12 E2E: `scripts/playwright_st_06_12_lint_panel_navigation_e2e.py` (opens lint panel, verifies F8/Shift-F8 + Mod-Alt-n/p, checks quick-fix buttons appear in the panel).
- Frontend auth: align register response typing by not reading `csrf_token` from `RegisterResponse` (`frontend/apps/skriptoteket/src/stores/auth.ts`).
- EPIC-14 ongoing: see `docs/backlog/sprints/sprint-2026-01-05-tool-editor-vertical-slice.md`.

## Verification

- Docs: `pdm run docs-validate` (pass)
- SPA typecheck: `pnpm -C frontend --filter @skriptoteket/spa typecheck` (pass)
- SPA lint: `pnpm -C frontend --filter @skriptoteket/spa lint` (pass)
- Frontend tests: `pdm run fe-test` (pass)
- SPA build: `pdm run fe-build` (pass)
- UI (editor smoke): `pdm run ui-editor-smoke` (pass; artifacts in `.artifacts/ui-editor-smoke/`; Playwright required escalation on macOS)
- UI (ST-06-11): `pdm run python -m scripts.playwright_st_06_11_quick_fix_actions_e2e` (pass; artifacts in `.artifacts/st-06-11-quick-fix-actions-e2e/`; Playwright required escalation on macOS)
- UI (ST-06-12): `pdm run python -m scripts.playwright_st_06_12_lint_panel_navigation_e2e` (pass; artifacts in `.artifacts/st-06-12-lint-panel-navigation-e2e/`; Playwright required escalation on macOS)

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

## Next Steps

- ST-06-13: lint gutter filtering/polish (markerFilter/tooltipFilter) and severity policy.
- ST-08-14: CodeMirror ghost-text integration with Tabby (ADR-0043 + ADR-0050); see `docs/runbooks/runbook-tabby-codemirror.md` for API client code.
