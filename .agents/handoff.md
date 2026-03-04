# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-04
- Branch: `main`
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: ADR-0067 pivot + PR-0060 updates; legacy SDS fetch pipeline removed.

## Current Session (2026-03-04)

- Docs pivot to ADR-0067 (markdown-first offline SDS corpus):
  - `docs/adr/adr-0067-reagent-prep-chef-sds-markdown-first-offline-corpus.md`
  - `docs/backlog/epics/epic-20-curated-app-reagent-prep-chef.md`
  - `docs/backlog/stories/story-20-02-curated-app-reagent-prep-chef-risk-assessment.md`
  - `docs/backlog/prs/pr-0060-curated-app-reagent-prep-chef-risk-assessment.md`
- Repo-owned SDS corpus (commit markdown; PDFs optional outside git):
  - Markdown: `data/reagent_prep_chef/sds/markdown/`
  - Index + gaps: `data/reagent_prep_chef/sds/index.json`, `data/reagent_prep_chef/sds/gaps.md`
  - Scripts: `scripts/sync_reagent_prep_chef_sds_markdown.py`, `scripts/build_reagent_prep_chef_sds_index.py`
- Backend: offline SDS store + markdown endpoint; Riskbedömning simplified (no fetch/no derived signals):
  - Store: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_store.py`
  - Routes: `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`
  - Risk handler: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`
- Cleanup: removed legacy PubChem/SDS fetch pipeline (infrastructure + CLI + tests) per ADR-0067.
- UI: Riskbedömning shows curated safety + SDS modal (markdown):
  - `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefStepRisk.vue`
  - `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefSdsModal.vue`
  - `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefRisk.ts`
- Older history: see `.agents/readme-first.md` + `docs/` (PR-0062 is canceled).

## Verification

- 2026-03-04: `pdm run format`, `pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run docs-validate`
- 2026-03-04: OpenAPI + SPA types: `pdm run openapi-export-v1`, `pdm run fe-gen-api-types`, `pdm run fe-type-check`
- 2026-03-04: SDS index regeneration: `pdm run python scripts/build_reagent_prep_chef_sds_index.py`
- 2026-03-04: Live check (dev-local + Playwright):
  - `docker compose up -d db && pdm run db-upgrade`
  - `pdm run dev-local`
  - `pdm run playwright install chromium`
  - `pdm run python -m scripts.playwright_st_11_09_curated_app_e2e --base-url http://127.0.0.1:5173`

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

- PR-0069: fix Docker deployments so the web container can read `data/reagent_prep_chef/sds/index.json` and Riskbedömning
  can open SDS markdown in-app (no `SDS index not found`).
- PR-0068: download SDS PDF originals for the 25 missing keys in `data/reagent_prep_chef/sds/gaps.md` and store them
  outside git under `data/reagent_prep_chef/sds/files/` using `<key>__<provider>__<revision>.pdf`.
- PR-0067: convert PDFs → Swedish markdown, sync into `data/reagent_prep_chef/sds/markdown/`, then rebuild index/gaps
  until `data/reagent_prep_chef/sds/gaps.md` shows `Missing markdown: 0`.
- Close PR-0060 acceptance: confirm Riskbedömning export/save flows + OpenAPI/TS types regeneration.
