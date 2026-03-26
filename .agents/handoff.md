# Session Handoff
Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-26
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`

## Status

- Hemma is clean and Git-aligned after the reset/redeploy sequence; `sir_convert_a_lot_prod`, `skriptoteket-web`, and `skriptoteket-worker` are healthy.
- `PR-0137` shipped the class-list import remediation:
  - example corpus under `data/class_list_example_inputs/` parses across `.txt` / `.csv` / `.tsv` / `.xls` / PDF-backed fixtures and create/edit class-list flows expose in-modal `Importera från fil`
  - successful imports reconcile into overview state, edit-mode imports no longer remap student IDs by row position, and roster student-list replacement is still blocked while an active draft depends on the class list
- `PR-0138` shipped the Sir Convert runtime-policy cleanup:
  - this repo now uses only `SIR_CONVERT_A_LOT_V2_API_KEY`
  - local Skriptoteket defaults to the Hemma/public Sir Convert lane
  - the sibling `sir-convert-a-lot` repo now has an explicit CPU-only local Docker dev profile
- `PR-0144` now has a first host-runtime recovery slice in place:
  - host `Settings()` normalize container-only local defaults onto `/tmp/skriptoteket/artifacts` and `/tmp/skriptoteket/vault` when running outside Docker in development
  - host `Settings()` rewrite `SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:8085` to `http://127.0.0.1:8085` for host-run dev processes while keeping the callback URL on `host.docker.internal:8000` for the Dockerized Sir Convert callback lane
  - after local DB/bootstrap recovery, the host-side `smoke-seating-export-readiness` passed again and produced a Vault-backed PDF from the `127.0.0.1` lane
- `PR-0145` is now implemented locally:
  - `scripts/check_migration_test_coverage.py` now enforces explicit integration coverage for all 49 Alembic revisions
  - `migrations/versions/0032_user_file_vault.py` now refreshes inspection state before index creation, so fresh upgrades keep the `user_vault_files` indexes and host `pdm run db-upgrade` reruns no-op cleanly
- `PR-0142` shipped the first locked EPIC-26 export slice for seating XLSX:
  - seating export contract now supports `pdf` and `xlsx` without a compatibility shim; `layout_id` / `paper_size` are nullable only for XLSX
  - seating keeps `Affisch (A3)` as the default action and exposes `Excel (.xlsx)` as a menu option
  - XLSX generation is local `openpyxl` delivery through `SeatingXlsxRenderer`, not Sir Convert
  - seating download delivery now returns the media type from the stored artifact instead of assuming PDF
  - key files: `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py`, `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_xlsx_renderer.py`, `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportApi.ts`, `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts`
- `PR-0143` is now implemented locally and `ST-26-03` is marked done:
  - the seating workbook is now a single-sheet `Sittplacering` artifact that preserves the classroom as a spatial grid instead of flattening seats into a table
  - empty seats and aisle gaps remain explicit, unplaced students render in a compact section below the grid, and the unplaced section is skipped entirely when everyone is seated
  - the local workbook proof in `.artifacts/epic26-pr0143-workbook-check/` confirms the printed sheet stays clean enough to share or save as PDF without a duplicate presentation tab
- `PR-0139` is now implemented locally and verified on the host lane:
  - grouping now has its own export action hierarchy with `Exportera` defaulting to `Excel (.xlsx)` and a compact adjacent menu for `Excel (.xlsx)` and `PDF (A4 stående)`
  - backend/frontend now share a dedicated `GroupingExportPresentation` contract plus grouping-specific export job routes, DTOs, persistence, and reload recovery
  - grouping export jobs are currently deliberate placeholder scaffolding in dev: real jobs are created, stay recoverable in `submitted` / `processing`, and do not render final artifacts until `PR-0140` / `PR-0141`
  - key files: `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_exports.py`, `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`, `src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py`, `frontend/apps/skriptoteket/src/views/apps/useGroupingExportFlow.ts`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue`
- `PR-0140` is now implemented locally and `ST-26-05` is marked done:
  - grouping `xlsx` now completes locally, stores a Vault-backed artifact, and downloads as the default grouping export
  - the workbook uses a protected `Redigera grupper` sheet with a student reassignment table (`Nr i grupp`, `Elev`, `Grupp (välj)`), a separate `Gruppregister` table (`Grupp`, `Gruppordning (välj)`), concise in-sheet guidance, and locked non-editable surfaces
  - `Dela och exportera` stays formula-linked to the editable grouping surfaces for already assigned students, keeps blank-group rows out of the presentation, and prints cleanly with fixed spacing between group sections
  - key files: `src/skriptoteket/application/curated_apps/classroom_planner/exports/grouping_xlsx_view_model.py`, `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/grouping_xlsx_renderer.py`, `src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_export_jobs.py`
- `PR-0141` is now in progress and the grouping PDF slice is implemented locally:
  - grouping `PDF (A4 stående)` renders locally with WeasyPrint from export-owned HTML/CSS, uses the two-column paired card layout, and shows the Skriptoteket logo in the upper-right letterhead on the host `5173` lane
  - backend-owned shared branding assets now live under `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/assets/` so local host runs and Docker web containers resolve the same logo path
  - architecture pivot approved on 2026-03-26:
    - `ADR-0075` locks Klassrumskartan app-owned PDF artifacts to a local Skriptoteket render/finalize boundary
    - Sir Convert remains for general conversion workloads and class-list import extraction, not the final seating-PDF artifact path
  - the seating follow-up is now shipped through `PR-0146`:
    - seating `pdf` renders/finalizes locally through `WeasyPrintSeatingPdfRenderer`
    - seating-specific Sir Convert callback/webhook/reconciliation code is deleted
    - live `5173` proof now downloads a fresh branded seating PDF artifact
- Local 2026-03-25 delete-rule follow-up changed overview asset deletion semantics:
  - deleting a class list or classroom now removes dependent planner drafts instead of blocking on active-draft dependency
  - the overview confirmation dialogs and local error rendering were updated to match the cascade behavior
- Current planning/implementation focus is now split between EPIC-26 export follow-on and the first EPIC-27 smart-assignment slice:
  - [EPIC-26](docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md)
  - next locked export order and pacing: [PR-0141](docs/backlog/prs/pr-0141-klassrumskartan-grouping-pdf-a4-portrait-presentation-renderer-and-delivery.md)
  - lessons learned for the export lane: keep seating PDF default behavior untouched, keep seating XLSX teacher-facing and spatial instead of duplicating a presentation tab, and verify against the host `dev-local` lane rather than trusting container logs alone
  - `PR-0140` shipped the narrowed grouping workbook shape: linked reassignment/reordering for already assigned students, blank-group rows excluded from the presentation, and the edit sheet intentionally optimized for bounded dropdown/order tweaks rather than broad offline roster editing
  - migration guardrail added during `PR-0139`: `scripts/check_migration_test_coverage.py` now fails if Alembic has anything other than a single head, because recent operator-error incidents created split-head local states
- Smart-assignment planning docs are now approved and implementation has started:
  - decision memo: `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`
  - ADR / epic / review: `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md` (`accepted`), `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md` (`active`), `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md` (`approved`)
  - stories: `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` through `docs/backlog/stories/story-27-05-klassrumskartan-smart-explanations-and-alternate-options.md`
  - locked product shape: per-mode `Smart` toggles beside `Slumpa`, export-only checkpoints, no migration/compat layer for old metadata, seating + grouping smart mode day one, and grouping-specific seating-distance toggle
  - post-review tightening already applied: shared-vs-mode-specific controls are now explicit, grouping checkpoints are the future primary grouping-history lane, `Use history` blocks when no eligible checkpoints exist, canonical assignment-hash semantics are defined, and `En smart variant till` now requires a distinct result or a short no-further-variant message
  - `ST-27-01` is now `in_progress` and its first delivered slice is:
    - new persisted `smart_enabled` draft flag in domain/API/repository + Alembic migration `e4b7c2d9a1f0_add_smart_enabled_to_classroom_planner_drafts.py`
    - small `Smart` toggles rendered beside `Slumpa` in both grouping and seating workspaces
    - old visible notes/proximity/stability drawer no longer opens from the workspace shell
  - remaining `ST-27-01` scope still to implement:
    - full visible control reset to `Support seat`, `Keep apart`, `Keep near`, `Use history`
    - hard deletion of old student-planning semantics from runtime/persistence
    - normalized persistence + UI flows for smart relation controls

## Verification

- 2026-03-25 overview asset delete cascade follow-up:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_asset_delete_guards.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/web/apps/classroom_planner/test_api.py`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
  - live proof with dev service on `http://127.0.0.1:5173/apps/classroom.group-seating-studio` via one-off `pdm run python - <<'PY' ... PY`:
    - created temporary roster/template pairs plus active seating drafts, then verified roster deletion returned workspace-summary `404` and template deletion cleared the dependent active seating draft
    - artifacts: `.artifacts/roster-template-delete-cascade-proof/before-roster-delete.png`, `.artifacts/roster-template-delete-cascade-proof/after-roster-delete.png`, `.artifacts/roster-template-delete-cascade-proof/before-template-delete.png`, `.artifacts/roster-template-delete-cascade-proof/after-template-delete.png`
- 2026-03-26 PR-0143 seating XLSX workbook completion:
  - tests/docs passed; workbook proof artifacts remain under `.artifacts/epic26-pr0143-workbook-check/`
- 2026-03-26 PR-0139 grouping export hierarchy + shared contract:
  - frontend/backend tests, migration-head guard, and host proof passed; artifacts remain under `.artifacts/epic26-pr0139-host-check/`
- 2026-03-26 PR-0140 grouping XLSX workbook + delivery:
  - renderer/job/API tests and host workbook proofs passed; artifacts remain under `.artifacts/epic26-pr0140-registry-check/` and `.artifacts/epic26-pr0140-spacing-check/`
- 2026-03-26 PR-0141 grouping PDF + boundary diagnosis:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_seating_export_job_support.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_poster_renderer.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_grouping_pdf_renderer.py`
  - `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_support.py src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/poster_renderer.py src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/pdf_branding.py tests/unit/application/apps/classroom_planner/test_seating_export_job_support.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_poster_renderer.py`
  - `pdm run docs-validate`
  - host proof on `http://127.0.0.1:5173/apps/classroom.group-seating-studio` via temporary repo Playwright script:
    - grouping `PDF (A4 stående)` downloads successfully and shows the Skriptoteket logo letterhead
    - artifact: `.artifacts/epic26-pr0141-host-check/grouping-a4-page-1.png`
  - direct seating renderer isolation:
    - `poster_renderer.py` emits logo-bearing HTML and local WeasyPrint renders it correctly
    - artifacts: `.artifacts/epic26-root-cause-seating/index.html`, `.artifacts/epic26-root-cause-seating/local-weasy-inline-page-1.png`
  - sibling `sir-convert-a-lot` repo inspection on 2026-03-26:
    - `scripts/sir_convert_a_lot/infrastructure/weasyprint_html_to_pdf.py` blocks `data:` resources in the restricted fetcher
    - `scripts/sir_convert_a_lot/domain/specs_v2.py` defaults `conversion.input_trust_mode` to `UNTRUSTED_UPLOAD`
    - this confirmed the service-boundary seam was the wrong architectural fit for Klassrumskartan-owned PDFs
- 2026-03-26 PR-0146 seating PDF local cutover + route root cause:
  - backend cutover:
    - seating `pdf` jobs now render locally in `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_pdf_renderer.py`
    - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py` now completes seating PDF jobs locally and no longer submits seating artifacts to Sir Convert
    - deleted seating-only callback/webhook/reconciliation files:
      - `src/skriptoteket/web/api/v1/internal_sir_convert_callbacks.py`
      - `src/skriptoteket/cli/commands/reconcile_seating_export_webhooks.py`
      - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_webhook_reconciliation.py`
      - `src/skriptoteket/application/curated_apps/classroom_planner/exports/webhook_contract.py`
      - `src/skriptoteket/application/curated_apps/classroom_planner/exports/webhook_bindings.py`
      - `src/skriptoteket/infrastructure/repositories/classroom_planner_export_webhook_bindings.py`
  - root-cause diagnosis for the stock Playwright/login helper failure:
    - login was healthy; the real blocker was `/api/v1/apps/classroom.group-seating-studio/drafts/resumable` returning `500`
    - the live local DB schema was behind the active planner ORM
    - new Alembic revisions in the worktree remediate active smart-assignment-v1 persistence drift:
      - `migrations/versions/7b8a6f1d2c3e_add_missing_planner_draft_flags.py`
      - `migrations/versions/8c4d2e1f7a9b_add_missing_planner_smart_rule_tables.py`
  - verification:
    - `pdm run db-upgrade`
    - `pdm run pytest tests/unit/application/apps/classroom_planner/test_seating_export_jobs.py tests/unit/web/apps/classroom_planner/test_seating_export_job_api.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_poster_renderer.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_seating_pdf_renderer.py`
    - `pdm run pytest -o addopts='' 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[7b8a6f1d2c3e]' 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[8c4d2e1f7a9b]'`
    - `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_support.py src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_pdf_renderer.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/protocols/classroom_planner_exports.py src/skriptoteket/di/curated_apps.py src/skriptoteket/cli/commands/smoke_seating_export_readiness.py src/skriptoteket/web/router.py src/skriptoteket/cli/main.py tests/unit/application/apps/classroom_planner/test_seating_export_jobs.py tests/unit/web/apps/classroom_planner/test_seating_export_job_api.py tests/unit/infrastructure/curated_apps/apps/classroom_planner/test_seating_pdf_renderer.py tests/integration/migration_schema_assertions.py migrations/versions/7b8a6f1d2c3e_add_missing_planner_draft_flags.py migrations/versions/8c4d2e1f7a9b_add_missing_planner_smart_rule_tables.py`
    - `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_job_completion.py src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_pdf_renderer.py src/skriptoteket/infrastructure/repositories/classroom_planner.py`
    - `pdm run python -m scripts.playwright_pr_0141_seating_pdf_branding_check --base-url http://127.0.0.1:5173`
    - fresh live artifacts:
      - `.artifacts/epic26-pr0141-seating-branding-check/seating-export-a3.pdf`
      - `.artifacts/epic26-pr0141-seating-branding-check/seating-export-a3-page-1.png`
      - `.artifacts/epic26-pr0141-seating-branding-check/seating-export-status.png`

## How to Run

```bash
# Local dev
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Planner import browser proof
pdm run python -m scripts.playwright_pr_0137_class_list_import_check --base-url http://127.0.0.1:5173

# Hemma export deploy/readiness gate
ssh hemma 'cd ~/apps/skriptoteket && ./scripts/hemma_deploy_and_verify_seating_export.sh'
```

## Known Issues / Risks

- `http://127.0.0.1:5173/apps/classroom.group-seating-studio` currently resolves to the host `pdm run dev-local` Vite/uvicorn pair, not the Docker frontend/web ports:
  - `lsof -nP -iTCP:5173 -sTCP:LISTEN` shows host `node ... vite`
  - `lsof -nP -iTCP:8000 -sTCP:LISTEN` shows host `uvicorn ... --reload`
  - container logs can therefore look healthy while the page still fails against the host stack
- Host dev export smoke now matches the local Klassrumskartan PDF boundary:
  - seating and grouping PDFs both render locally in Skriptoteket on the host `dev-local` lane
  - the latest resumable-draft blocker was schema drift against active smart-assignment-v1 persistence, and the local worktree now carries the missing Alembic revisions plus passing idempotency checks
- `pdm.lock` still has local, uncommitted follow-up changes after the `pdfplumber` runtime fix; do not lose or silently overwrite that diff.
- `ST-26-02` and `EPIC-26` docs are still marked `ready` / unchecked even though `PR-0137` shipped; decide whether to mark them done after the lockfile follow-up and any final review closure.
- `ST-27-01` has only its first vertical slice in place; the deeper contract reset is still unfinished even though the review/ADR lane is approved.
- Current follow-up gap after `PR-0146` closeout:
  - Sir Convert cleanup stays gated behind the approved downstream cutover docs/review path and should not start until the downstream local-cutover proof is treated as the formal prerequisite

## Next Steps

- Keep Sir Convert cleanup blocked until the approved downstream-cutover gate is acknowledged:
  - one live seating export proof now exists on `http://127.0.0.1:5173`
  - only after that formal gate is accepted should the Sir Convert cleanup task remove the curated-app trusted-bundle path
- Continue `ST-27-01` from the delivered smart-toggle slice:
  - remove old student-planning runtime/persistence semantics fully
  - add new smart control persistence/contracts for `Support seat`, `Keep apart`, and `Keep near`
  - keep `Use history` as a contract-only placeholder until `ST-27-02` export checkpoints land
