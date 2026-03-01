# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-01
- Branch: `main`
- Current sprint: None (between sprints; last: `SPR-2026-01-05` (done))
- Production: Full Vue SPA
- Completed: history in `.agents/readme-first.md`

## Current Session (2026-03-01)

- Planned EPIC-21 conversion hub (Sir Convert-a-Lot v2) docs scaffolding: ADR-0066 + EPIC-21 + ST-21-01/02 +
  REV-EPIC-21 + PR-0063..PR-0066; verified `pdm run docs-validate`.

## Current Session (2026-02-13)

- Added parallel Story 003c provider-side planning story for Skriptoteket docs-as-code workflow:
  - `docs/backlog/stories/story-19-07-story-003c-thin-adapter-consumer-adoption-and-scientific-pdf-workload.md`
- Added PR-sized execution doc linked to ST-19-07:
  - `docs/backlog/prs/pr-0061-story-003c-thin-adapter-parity-and-scientific-pdf-workload-validation.md`
- Updated docs index entries:
  - `docs/index.md` (added ST-19-07, PR-0061, and missing `story-20-02` + `pr-0060` listings)

## Current Session (2026-02-18)

- Fixed `Mina filer` medium-width overflow in `VaultPanel` responsive toolbar: `frontend/apps/skriptoteket/src/components/vault/VaultPanel.vue`
- Live check: Playwright `/vault` responsive probe (dev-local) → `.artifacts/vault-responsive-check-20260218T084906/report.json` (+ screenshots)
- Started PR-0062 (Riskbedömning best-effort contract) with an infra “small slice” targeting the dominant SDS failure
  modes (heuristics/density/clp):
  - Backlog doc: `docs/backlog/prs/pr-0062-curated-app-reagent-prep-chef-risk-assessment-best-effort-contract.md`
  - Best-effort SDS caching semantics:
    `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_index_store.py`,
    `src/skriptoteket/infrastructure/curated_apps/apps/reagent_prep_chef/sds_fetcher.py`,
    `src/skriptoteket/domain/curated_apps/reagent_prep_chef/models.py`,
    `src/skriptoteket/protocols/reagent_prep_chef.py`
  - Assumption validation CLI: `src/skriptoteket/cli/commands/validate_sds_assumptions.py`
  - Unit tests: `tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_index_store.py`
  - Validation artifacts:
    `.artifacts/sds-cache/assumption-validation-heuristics.json` and cached PDFs under
    `.artifacts/sds-cache-assumptions/files/`
- PR-0062 backend slice: risk draft now runs best-effort (`require_complete=False`) and returns explicit
  `missing_flags` + `export_gate` derived from SDS cache completeness:
  - Contract: `src/skriptoteket/application/curated_apps/reagent_prep_chef.py`
  - Handler: `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`
  - Route: `src/skriptoteket/web/api/v1/apps_reagent_prep_chef.py`
  - Tests: `tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py`
- PR-0062 frontend slice: export/save gated by `draft.export_gate.ready`; SDS button gated by `draft.sds.pdf_available`:
  - `frontend/apps/skriptoteket/src/composables/reagentPrepChef/useReagentPrepChefRisk.ts`,
    `frontend/apps/skriptoteket/src/views/apps/reagent-prep-chef/ReagentPrepChefStepRisk.vue`,
    `frontend/apps/skriptoteket/src/api/openapi.d.ts`
- PR-0062 SDS pipeline slice history + evidence is kept in:
  - `docs/backlog/prs/pr-0062-curated-app-reagent-prep-chef-risk-assessment-best-effort-contract.md`

## Current Session (2026-02-28)

- PR-0062 Slice 6.10: reran truthy sample v1 with fresh cache root → `.artifacts/sds-cache/slice-6-10-report.json` (`ok=6 partial=8 fail=7`).
- PR-0062 Slice 6.11: curated Roth SDS linkouts for `C2H6O`/`C7H6O2`/`K2Cr2O7` (CIDs `702`/`243`/`24502`) → `data/sds_linkouts/curated.json`.
  - Evidence: `.artifacts/sds-cache/slice-6-11-report.json` (`ok=1 partial=2 fail=0`) + `.artifacts/sds-cache/slice-6-11-scl-snippets/`.
- PR-0062 Slice 6.12: reran full truthy sample v1 with fresh cache root → `.artifacts/sds-cache/slice-6-12-report.json` (`ok=7 partial=10 fail=4`).
  - Remaining fresh-cache fails: `NH4NO3`, `Ca(OH)2`, `C7H6O3`, `S`.
- PR-0062 Slice 6.13 (Option B): allow best-effort export when SCL/CLP bands are missing by falling back to SDS-level
  hazard signals (`hazard_codes`/`pictograms`/`signal_word`) with explicit notes; keep missing flags but remove
  `sds_clp_bands_missing` and `clp_unavailable_for_target` from export-blocking:
  - `src/skriptoteket/application/curated_apps/handlers/reagent_prep_chef_risk_assessment.py`
  - `tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py`
- PR-0062 Slice 6.14: curated SDS linkouts for the remaining FAIL keys (`NH4NO3`, `Ca(OH)2`, `C7H6O3`, `S`) so they
  now seed as truthy PDFs (`fail → partial`):
  - `data/sds_linkouts/curated.json`
  - Evidence: `.artifacts/sds-cache/slice-6-14-report.json` (`ok=0 partial=4 fail=0`) + `.artifacts/sds-cache/slice-6-14-scl-snippets/`
- PR-0062 Slice 6.15: reran full truthy sample v1 with fresh cache root → `.artifacts/sds-cache/slice-6-15-report.json`
  (`ok=7 partial=14 fail=0`).
- PR-0062 Slice 6.16: full seed run (164 hazards) with fresh cache root → `.artifacts/sds-cache/slice-6-16-report.json`
  (`ok=11 partial=14 fail=139 total=164`).
  - FAIL taxonomy (pinned from seed log): `.artifacts/sds-cache/slice-6-16-fail-attempts.json` (`no_candidates=79`,
    `non_sds_candidates=59` dominated by NJ “RTK Act” + CAS terms, `pdf_no_hazard_codes=1`).

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
- Older history: see `.agents/readme-first.md` + `docs/`.

## Verification

- 2026-02-28: `pdm run docs-validate`
- 2026-02-28: `PYTHONPATH=src pdm run pytest -q tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_fetcher_density_selection.py tests/unit/infrastructure/curated_apps/apps/test_reagent_prep_chef_sds_clp_bands_parser.py`
- 2026-02-28: `PYTHONPATH=src pdm run pytest -q tests/unit/application/curated_apps/handlers/test_reagent_prep_chef_risk_assessment_best_effort.py`
- 2026-02-28: Slice 6.11 seed (fresh cache root): `ARTIFACTS_ROOT=.artifacts/sds-cache/slice-6-11-cache-root PYTHONPATH=src pdm run python -m skriptoteket.cli seed-sds-cache --best-effort --no-fail-fast --concurrency 1 --only 'C2H6O' --only 'C7H6O2' --only 'K2Cr2O7' --report .artifacts/sds-cache/slice-6-11-report.json`
- 2026-02-28: Slice 6.12 seed command + `--only` list is in the PR doc; outputs: `.artifacts/sds-cache/slice-6-12-report.json`, `.artifacts/sds-cache/slice-6-12-seed.log`
- 2026-02-28: Slice 6.14 seed (fresh cache root; remaining FAIL keys): outputs `.artifacts/sds-cache/slice-6-14-report.json`, `.artifacts/sds-cache/slice-6-14-seed.log`
- 2026-02-28: Slice 6.15 seed command + `--only` list is in the PR doc; outputs: `.artifacts/sds-cache/slice-6-15-report.json`, `.artifacts/sds-cache/slice-6-15-seed.log`

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

- PR-0062 Slice 6: use the Slice 6.16 taxonomy to decide whether to (a) expand SDS provider coverage, or (b) treat SDS
  prefetch as opportunistic and prioritize best-effort risk draft/export UX while curating only high-value SDS PDFs.
- Decide whether `clp_bands` should remain tracked as “partial” in seed reports now that Option B makes export
  best-effort w.r.t. SCL, or if we should split “export-blocking missing” vs “nice-to-have missing” in the seed report.
