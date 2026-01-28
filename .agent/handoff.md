# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-01-28
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: history in `.agent/readme-first.md`

## Current Session (2026-01-28)

- Riskbedömning workflow added for Reagent Prep Chef:
  - Backend models + handlers + routes: `src/skriptoteket/application/curated_apps/reagent_prep_chef.py`,
    `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`,
    `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_export_risk_pdf.py`,
    `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_save_risk_pdf.py`,
    `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`
  - Curated data + SDS store + risk templates: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/`
  - DI wiring: `src/skriptoteket/di/curated_apps.py`
  - SPA Riskbedömning tab + API calls: `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue`
  - Tests: `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_risk_templates_store.py`,
    `tests/unit/domain/curated_apps/reagent_prep_chef/test_risk_assessment.py`,
    `tests/unit/web/reagent_prep_chef/`

- Curated app planning docs added (Reagent Prep Chef):
  - Spec: `docs/reference/ref-curated-app-reagent-prep-chef.md`
  - Epic/Story/Review/PR: `docs/backlog/epics/epic-20-curated-app-reagent-prep-chef.md`,
    `docs/backlog/stories/story-20-01-curated-app-reagent-prep-chef.md`,
    `docs/backlog/reviews/review-epic-20-curated-app-reagent-prep-chef.md`,
    `docs/backlog/prs/pr-0059-curated-app-reagent-prep-chef.md`
  - Verification: `pdm run docs-validate`

- Curated apps: `ui_mode` added to registry + `/api/v1/apps/{app_id}`; `chemistry.reagent_prep_chef` is `bespoke_required`.
  - Backend registry + execution: `src/skriptoteket/infrastructure/curated_apps/`
  - Reagensberedning app backend: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/`
  - SPA route host + bespoke view: `frontend/apps/skriptoteket/src/views/AppHostView.vue`,
    `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue`
  - UX: always land on Step 1 (Ämne) after reload (avoid blank intermediate steps): `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue`
  - OpenAPI types refreshed: `pdm run fe-gen-api-types`

- Vault UI (file refs):
  - New authenticated route: `frontend/apps/skriptoteket/src/views/VaultView.vue` (path: `/vault`)
  - Vault panel + picker modal: `frontend/apps/skriptoteket/src/components/vault/`
  - Vault API composable: `frontend/apps/skriptoteket/src/composables/vault/useVaultFiles.ts`
  - Tool run artifacts: save to vault + pass `runId`: `frontend/apps/skriptoteket/src/components/tool-run/ToolRunArtifacts.vue`
  - File-ref pickers support session + vault sources:
    `frontend/apps/skriptoteket/src/components/tool-run/ToolFileFieldPicker.vue`,
    `frontend/apps/skriptoteket/src/components/ui-actions/UiActionFieldFileRef.vue`
  - E2E: `scripts/playwright_st_14_36_vault_ui_e2e.py`

- Auth UX hardening: timeout auth fetches to avoid stuck "Loggar in…": `frontend/apps/skriptoteket/src/stores/auth.ts`

- Older history: see `.agent/readme-first.md` + `docs/`.

## Verification

- Backend (host): `pdm run dev-logs` (background) + `curl -sSf http://127.0.0.1:8000/healthz`
- Frontend (Vite): `pdm run fe-dev-logs` (background) + `curl -sSf http://127.0.0.1:5173/`
- Dev-local (backend + SPA): `pdm run dev-local` (backend `:8000`, Vite `:5173`).
- Playwright (macOS may need escalation): `pdm run python -m scripts.playwright_st_11_09_curated_app_e2e --base-url http://127.0.0.1:5173`
  → artifacts: `.artifacts/st-11-09-curated-app-e2e/` (demo.counter + Reagensberedning).
- Playwright (vault flow): `pdm run python -m scripts.playwright_st_14_36_vault_ui_e2e --base-url http://127.0.0.1:5173`
  → artifacts: `.artifacts/st-14-36-vault-ui-e2e/`
- Playwright smoke (includes `/vault`): `BASE_URL=http://127.0.0.1:5173 pdm run ui-smoke`
- Quality gates:
  - `pdm run format`
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run test`
  - `pdm run fe-gen-api-types`
  - `pdm run fe-type-check`
  - `pdm run fe-lint`

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Quality gates
pdm run lint
pdm run typecheck
pdm run test
pdm run fe-test
```

## Known Issues / Risks

- Local Devstral inline completions remain slow (~8–9s provider_ms in logs) and still return off-target blocks in long-script holes.
- Playwright on macOS may require escalated permissions (MachPortRendezvous).

## Next Steps

- Consider reducing system prompt weight or adding explicit local context metadata to improve completion relevance.
