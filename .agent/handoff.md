# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agent/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-02-18
- Branch: `main` + local changes
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: history in `.agent/readme-first.md`

## Current Session (2026-02-13)

- Added parallel Story 003c provider-side planning story for Skriptoteket docs-as-code workflow:
  - `docs/backlog/stories/story-19-07-story-003c-thin-adapter-consumer-adoption-and-scientific-pdf-workload.md`
- Added PR-sized execution doc linked to ST-19-07:
  - `docs/backlog/prs/pr-0061-story-003c-thin-adapter-parity-and-scientific-pdf-workload-validation.md`
- Updated docs index entries:
  - `docs/index.md` (added ST-19-07, PR-0061, and missing `story-20-02` + `pr-0060` listings)

## Current Session (2026-02-18)

- Fixed `Mina filer` medium-width overflow in `VaultPanel` responsive toolbar:
  - `frontend/apps/skriptoteket/src/components/vault/VaultPanel.vue`
  - Kept toolbar stacked/wrapping through medium widths and delayed full horizontal split to `lg`.
  - Allowed search block to shrink before `lg` and made bulk actions full-width on narrow/medium layouts.
- Live functional check completed on `/vault` using Playwright against local `dev-local` services; screenshots + metrics:
  - `.artifacts/vault-responsive-check-20260218T084906/report.json`
  - `.artifacts/vault-responsive-check-20260218T084906/vault-*.png`

## Current Session (2026-02-01)

- SDS pipeline reliability + curated meta:
  - Curated meta store now loads (added `as_of`) and is used **before** PubChem density fetch.
  - Curated meta sources now included in SDS `sources` when used.
  - Sample seed run for `C3H6O`, `Al`, `AlCl3`, `AlCl3·6H2O`, `Al2O3` completes cleanly.
- Full prefetch run (164 hazards): ok=10, fail=154 → missing list in `.artifacts/sds-cache/missing-hazards.txt` (full report `.artifacts/sds-cache/full-report.json`).
- Tests + quality gates:
  - `pdm run format`, `pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run fe-test`.

## Current Session (2026-01-31)

- SDS pipeline refactor + LOC compliance for Riskbedömning:
  - Split SDS parsing into `sds_parsers/` package and introduced `sds_result_builder.py`.
  - Concentration-dependent CLP bands (min/max) parsed from SDS text using density + molar mass.
  - PDF SDS caching/serving via index store; export requires cached SDS only.
  - Multi-source SDS provider registry wired: `sds_pdf_providers.py` + catalog file.
- SPA refactor for LOC limits:
  - Split `frontend/apps/skriptoteket/src/views/apps/ReagentPrepChefView.vue` into step components and composables under
    `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/` and
    `frontend/apps/skriptoteket/src/composables/reagentPrepChef/`.
- UI check: Vite served SPA via `pdm run fe-dev-logs` and `curl -sSf http://127.0.0.1:5173/`.
- Docs progress updates:
  - `docs/backlog/prs/pr-0060-curated-app-reagent-prep-chef-risk-assessment.md`
  - `docs/backlog/stories/story-20-02-curated-app-reagent-prep-chef-risk-assessment.md`
  - `docs/backlog/epics/epic-20-curated-app-reagent-prep-chef.md`

## Current Session (2026-01-30)

- SDS pipeline reliability updates:
  - Hydrate multiplier parsing + CID expansion to resolve missing GHS data; PubChem client protocol typing.

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

- 2026-02-13: `pdm run docs-validate`
- 2026-02-18: `docker compose up -d db`, `pdm run db-upgrade`,
  `pdm run bootstrap-superuser --email "$BOOTSTRAP_SUPERUSER_EMAIL" --password "$BOOTSTRAP_SUPERUSER_PASSWORD"`,
  `pdm run dev-local`
- 2026-02-18: Playwright live `/vault` responsive check via `pdm run python - <<'PY' ...` (requests login + viewport probe at 1366/1240/1120/1024 widths)
  → no overflow/clipping (`docOverflow=False`, `toolbarClipped=False`, `bulkClipped=False`), report:
  `.artifacts/vault-responsive-check-20260218T084906/report.json`
- 2026-02-18: `pdm run fe-test` (pass, 46 files / 247 tests)
- 2026-01-31: `pdm run format`, `pdm run lint`, `pdm run typecheck`, `pdm run test`,
  `pdm run fe-test`, `pdm run docs-validate`, `pdm run fe-dev-logs`,
  `curl -sSf http://127.0.0.1:5173/`
- 2026-02-01: `pdm run format`, `pdm run lint`, `pdm run typecheck`, `pdm run test`,
  `pdm run fe-test`,
  `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts LOG_LEVEL=INFO SDS_FETCH_TIMEOUT_SECONDS=10 SDS_FETCH_LISTKEY_MAX_SECONDS=10 SDS_FETCH_LISTKEY_POLL_SECONDS=0.5 SDS_FETCH_AUTOCOMPLETE_LIMIT=10 PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache --no-fail-fast --report .artifacts/sds-cache/sample-report.json --concurrency 5 --only C3H6O --only Al --only AlCl3 --only "AlCl3·6H2O" --only Al2O3`
  `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts LOG_LEVEL=INFO SDS_FETCH_TIMEOUT_SECONDS=10 SDS_FETCH_LISTKEY_MAX_SECONDS=10 SDS_FETCH_LISTKEY_POLL_SECONDS=0.5 SDS_FETCH_AUTOCOMPLETE_LIMIT=10 PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache --no-fail-fast --report .artifacts/sds-cache/full-report.json --concurrency 5`
- 2026-01-30: `pdm run format`, `pdm run lint`, `pdm run typecheck`, `pdm run test`,
  `pdm run fe-gen-api-types`, `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-test`
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
