# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-20
- Branch: `main` + local changes
- Current sprint: N/A (no sprints)
- Production: Full Vue SPA
- Completed: Epic-23 Planning / ADR-0069 for Klassrumskartan.

## Current Session (2026-03-20)

- Klassrumskartan (Group Seating Studio) Document Architecture (Slice 1) Baseline approved.
  - `docs/adr/adr-0069-group-seating-studio-domain-model.md`
  - `docs/backlog/epics/epic-23-group-seating-studio.md`
  - `docs/backlog/reviews/review-epic-23-group-seating-studio.md`
  - Defined explicit Reducers and Domain Invariants separating Groups and Seats mapping to `student_id`.
  - Splitted baseline into exact 6 PR-sized Stories (`ST-23-01` to `ST-23-06`).
- Scaffolded frontend App shell `ClassroomPlannerView.vue` and normalized state stub `useClassroomState.ts`. Wait for `/bootstrap` prior to displaying layout.

## Previous Sessions

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
- Backend: SDS PDF is rendered from markdown (Skriptoteket-branded) and cached on disk:
  - Store: `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_store.py`
  - Cache dir: `Settings.REAGENT_PREP_CHEF_SDS_PDF_CACHE_DIR` (`src/skriptoteket/config.py`)
  - Dev mount: `compose.dev.yaml` → `./.artifacts/reagent_prep_chef/sds_pdfs:/var/lib/skriptoteket/reagent_prep_chef/sds_pdfs`
  - Prod mount (hemma): `compose.prod.yaml` → `/home/paunchygent/models/skriptoteket/reagent_prep_chef/sds_pdfs:/var/lib/skriptoteket/reagent_prep_chef/sds_pdfs`
- Cleanup: removed legacy PubChem/SDS fetch pipeline (infrastructure + CLI + tests) per ADR-0067.
- UI: Riskbedömning shows curated safety + SDS modal (markdown):
  - `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefStepRisk.vue`
  - `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefSdsModal.vue`
  - `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefRisk.ts`
- PR-0071 delivered (source-backed minimum + aligned gating/export naming):
  - New source note + mapping/decision checkpoint: `docs/reference/ref-reagent-prep-chef-riskunderlag-skolpraxis.md`
  - Backend single source of truth for required context:
    `src/skriptoteket/application/curated_apps/reagent_prep_chef_risk_contract.py`
  - Frontend “saknas”-copy now driven from `draft.export_gate.missing_context_fields`:
    `frontend/apps/skriptoteket/src/composables/reagentPrepChef/riskExportGate.ts`
  - Export/save naming updated to `underlag-riskbedomning*.pdf`:
    `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_export_risk_pdf.py`
- PR-0072 slice delivered (hazards↔SDS shortcards alignment):
  - New alignment script: `scripts/align_reagent_prep_chef_hazard_codes_from_shortcards.py`
  - Applied backfill from shortcards to hazards (`108` entries):
    `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/hazards.json`
  - New invariants/tests:
    - `tests/unit/scripts/test_align_reagent_prep_chef_hazard_codes_from_shortcards.py`
    - `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_hazards_store.py`
  - Alignment report artifact:
    `.artifacts/reagent_prep_chef/hazard-sds-alignment-report.json`
- PR-0072 follow-up slice delivered (drift guard policy):
  - New guard script:
    `scripts/check_reagent_prep_chef_hazard_shortcard_alignment.py`
  - New tests:
    `tests/unit/scripts/test_check_reagent_prep_chef_hazard_shortcard_alignment.py`
  - Guard wired into:
    - `pyproject.toml` (`lint` composite + `sds-check-hazard-alignment`)
    - `.pre-commit-config.yaml` (`reagent-hazard-shortcard-guard`)
  - Policy reference doc:
    `docs/reference/ref-reagent-prep-chef-hazard-shortcard-alignment-policy.md`
- PR-0073 delivered (textbook corpus immutable baseline + reconciliation):
  - Baseline/reconciliation script:
    `scripts/build_textbook_corpus_baseline.py`
  - Tests:
    `tests/unit/scripts/test_build_textbook_corpus_baseline.py`
  - PDM alias:
    `pdm run textbook-corpus-baseline`
  - Follow-up hardening: baseline output path now fails closed on non-empty dirs unless
    `--allow-overwrite` is explicitly passed.
- Older history: see `.agents/readme-first.md` + `docs/` (PR-0062 is canceled).

## Verification

- 2026-03-20: `pdm run docs-validate` passed with zero errors breaking the docs-contract.- 2026-03-04: `pdm run format`, `pdm run lint`, `pdm run typecheck`, `pdm run test`, `pdm run docs-validate`
- 2026-03-04: OpenAPI + SPA types: `pdm run openapi-export-v1`, `pdm run fe-gen-api-types`, `pdm run fe-type-check`
- 2026-03-04: SDS index regeneration: `pdm run python scripts/build_reagent_prep_chef_sds_index.py`
- 2026-03-04: SDS PDF unit checks:
  - `pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_store_pdf_cache.py`
  - `pdm run pytest -q tests/unit/web/reagent_prep_chef/test_chemicals_and_sds_routes.py`
- 2026-03-04: Docker dev rebuild after adding runtime dependency `markdown`:
  - `pdm run dev-rebuild`
- 2026-03-04: Live check: Vite proxy → backend returns PDF for SDS endpoint:
  - Login via Vite (`http://127.0.0.1:5173`) and `GET /api/v1/apps/chemistry.reagent_prep_chef/sds/NaHSO4` returns `Content-Type: application/pdf`
- 2026-03-04: Live check (dev-local + Playwright):
  - `docker compose up -d db && pdm run db-upgrade`
  - `pdm run dev-local`
  - `pdm run playwright install chromium`
  - `pdm run python -m scripts.playwright_st_11_09_curated_app_e2e --base-url http://127.0.0.1:5173`
- 2026-03-04: PR-0071 validation:
  - `pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_contract.py tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py tests/unit/web/reagent_prep_chef/test_risk_routes.py`
  - `pdm run fe-test -- src/composables/reagentPrepChef/riskExportGate.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run fe-lint`
  - `pdm run lint`
  - `pdm run typecheck`
  - `pdm run docs-validate`
  - Live functional check (backend+Vite already running): `pdm run python -m scripts.playwright_st_11_09_curated_app_e2e --base-url http://127.0.0.1:5173`
- 2026-03-04: PR-0072 slice validation:
  - `pdm run python -m scripts.align_reagent_prep_chef_hazard_codes_from_shortcards --apply`
  - `pdm run pytest -q tests/unit/scripts/test_align_reagent_prep_chef_hazard_codes_from_shortcards.py tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_hazards_store.py`
  - `pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py tests/unit/web/reagent_prep_chef/test_risk_routes.py`
  - `pdm run lint`
  - `pdm run typecheck`
- 2026-03-04: PR-0072 guard-policy validation:
  - `pdm run pytest -q tests/unit/scripts/test_check_reagent_prep_chef_hazard_shortcard_alignment.py`
  - `pdm run sds-check-hazard-alignment`
  - `pdm run lint`
  - `pdm run docs-validate`
- 2026-03-04: PR-0073 baseline validation:
  - `pdm run pytest -q tests/unit/scripts/test_build_textbook_corpus_baseline.py`
  - `pdm run ruff check scripts/build_textbook_corpus_baseline.py tests/unit/scripts/test_build_textbook_corpus_baseline.py`
  - `pdm run textbook-corpus-baseline --source-dir /Users/olofs_mba/Documents/Repos/html_to_pdf_handout_templates/Kemi --output-dir .artifacts/textbook_corpus/kemi-baseline --service-url http://127.0.0.1:28085`
- 2026-03-04: PR-0073 immutability hardening follow-up:
  - `pdm run pytest -q tests/unit/scripts/test_build_textbook_corpus_baseline.py`
  - `pdm run lint`
  - `pdm run docs-validate`

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

- PR-0072: If/when hazards contract adds `p_codes`, extend guard rules so P-code drift is blocking in CI as well.
- PR-0073: Add optional `--manifest-allowlist` so reconciliations can be scoped to a subset without changing source manifests.
