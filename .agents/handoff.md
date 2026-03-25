# Session Handoff
Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-25
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0137`, `PR-0138`, `PR-0142`, `PR-0145`

## Status

- Hemma is clean and Git-aligned after the reset/redeploy sequence:
  - `~/apps/sir-convert-a-lot` at `52f3d81`
  - `~/apps/skriptoteket` at `c09b17e`
  - `sir_convert_a_lot_prod`, `skriptoteket-web`, and `skriptoteket-worker` are healthy
- `PR-0137` shipped the class-list import remediation:
  - example corpus under `data/class_list_example_inputs/` parses across `.txt` / `.csv` / `.tsv` / `.xls` / PDF-backed fixtures
  - create/edit class-list flows expose in-modal `Importera från fil`
  - successful imports reconcile into overview state instead of reopening a blank modal
  - edit-mode imports no longer remap student IDs by row position
  - roster student-list replacement is blocked while an active draft depends on the class list
- `PR-0138` shipped the Sir Convert runtime-policy cleanup:
  - this repo now uses only `SIR_CONVERT_A_LOT_V2_API_KEY`
  - local Skriptoteket defaults to the Hemma/public Sir Convert lane
  - the sibling `sir-convert-a-lot` repo now has an explicit CPU-only local Docker dev profile
- `PR-0144` now has a first host-runtime recovery slice in place:
  - host `Settings()` normalize container-only local defaults onto `/tmp/skriptoteket/artifacts` and `/tmp/skriptoteket/vault` when running outside Docker in development
  - host `Settings()` rewrite `SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:8085` to `http://127.0.0.1:8085` for host-run dev processes while keeping the callback URL on `host.docker.internal:8000` for the Dockerized Sir Convert callback lane
  - after local DB/bootstrap recovery plus `reconcile-seating-export-webhooks`, the host-side `smoke-seating-export-readiness` passed again and produced a Vault-backed PDF from the `127.0.0.1` lane
- `PR-0145` is now implemented locally:
  - `scripts/check_migration_test_coverage.py` enforces explicit integration coverage for all 49 Alembic revisions
  - `tests/integration/test_migration_revision_coverage_idempotent.py` now covers the previously missing revisions from `0001_init` through `4a9d7c1e2b34`
  - the deterministic migration defect was in `migrations/versions/0032_user_file_vault.py`: it reused a stale inspector after `create_table(...)`, so fresh upgrades skipped the `user_vault_files` indexes
  - `0032_user_file_vault` now refreshes inspection state before index creation, the full uncovered-revision docker suite passes, and host `pdm run db-upgrade` reruns no-op cleanly
- `PR-0142` shipped the first locked EPIC-26 export slice for seating XLSX:
  - seating export contract now supports `pdf` and `xlsx` without a compatibility shim; `layout_id` / `paper_size` are nullable only for XLSX
  - seating keeps `Affisch (A3)` as the default action and exposes `Excel (.xlsx)` as a menu option
  - XLSX generation is local `openpyxl` delivery through `SeatingXlsxRenderer`, not Sir Convert
  - seating download delivery now returns the media type from the stored artifact instead of assuming PDF
  - key files: `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_export_jobs.py`, `src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/seating_xlsx_renderer.py`, `frontend/apps/skriptoteket/src/views/apps/classroomPlannerExportApi.ts`, `frontend/apps/skriptoteket/src/views/apps/useSeatingExportFlow.ts`
- The clean-checkout Hemma redeploy exposed one real packaging regression:
  - `class_list_document_extractor.py` imports `pdfplumber`
  - `pdfplumber` had only been declared in the `dev` dependency group
  - repo fix is committed and deployed via `c09b17e`
- Current local state:
  - `EPIC-26` export work is still in flight with multiple unrelated local changes
  - `EPIC-27` smart-assignment docs + first implementation slice are now also in the worktree
  - do not overwrite export-lane changes while continuing smart-assignment work
- Current planning/implementation focus is now split between EPIC-26 export follow-on and the first EPIC-27 smart-assignment slice:
  - [EPIC-26](docs/backlog/epics/epic-26-klassrumskartan-explicit-exports-and-class-list-import.md)
  - local verification was unblocked on 2026-03-25 by a clean DB reset + schema rebuild during the PR-0142 check
  - completed export slice: [PR-0142](docs/backlog/prs/pr-0142-klassrumskartan-seating-xlsx-menu-option-local-export-contract-and-flow.md)
  - next export slice: [PR-0143](docs/backlog/prs/pr-0143-klassrumskartan-seating-xlsx-workbook-layout-and-artifact-delivery.md)
  - follow with grouping export contract/UI via [PR-0139](docs/backlog/prs/pr-0139-klassrumskartan-grouping-export-action-hierarchy-and-shared-presentation-contract.md)
  - then [PR-0140](docs/backlog/prs/pr-0140-klassrumskartan-grouping-xlsx-workbook-layout-and-artifact-delivery.md) and [PR-0141](docs/backlog/prs/pr-0141-klassrumskartan-grouping-pdf-a4-portrait-presentation-renderer-and-delivery.md)
  - planned PR slices:
    - [PR-0142](docs/backlog/prs/pr-0142-klassrumskartan-seating-xlsx-menu-option-local-export-contract-and-flow.md)
    - [PR-0143](docs/backlog/prs/pr-0143-klassrumskartan-seating-xlsx-workbook-layout-and-artifact-delivery.md)
    - [PR-0139](docs/backlog/prs/pr-0139-klassrumskartan-grouping-export-action-hierarchy-and-shared-presentation-contract.md)
    - [PR-0140](docs/backlog/prs/pr-0140-klassrumskartan-grouping-xlsx-workbook-layout-and-artifact-delivery.md)
    - [PR-0141](docs/backlog/prs/pr-0141-klassrumskartan-grouping-pdf-a4-portrait-presentation-renderer-and-delivery.md)
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

## Previous Sessions

- Older shipped detail belongs in `.agents/readme-first.md` and the linked story/PR docs.
- Most relevant recent implementation docs:
  - `docs/backlog/prs/pr-0137-klassrumskartan-class-list-import-remediation-example-corpus-and-overview-reconciliation.md`
  - `docs/backlog/prs/pr-0138-seating-export-single-canonical-sir-convert-v2-key-and-runtime-wiring.md`
  - `docs/backlog/reviews/review-epic-26-klassrumskartan-explicit-exports-and-class-list-import.md`

## Verification

- 2026-03-25 PR-0142 seating XLSX export lane:
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/useSeatingExportFlow.spec.ts`
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_seating_export_jobs.py tests/unit/application/apps/classroom_planner/test_seating_export_webhook_dispatch.py tests/unit/web/apps/classroom_planner/test_seating_export_job_api.py`
  - `pdm run dev-db-reset`
  - `pdm run db-upgrade`
  - one-off local recovery: `PYTHONPATH=src pdm run python - <<'PY' ... PY` to bootstrap the local superuser and seed a smoke seating draft
  - one-off Playwright DOM checks against `http://127.0.0.1:5173/apps/classroom.group-seating-studio`:
    - default seating export request: `{"export_kind":"pdf","layout_id":"pretty_brutalist_poster","paper_size":"a3_landscape"}`
    - XLSX seating export request: `{"export_kind":"xlsx","layout_id":null,"paper_size":null}`
    - grouping workspace baseline: no export action, no export status surface, no `Exportera` copy
    - artifacts: `.artifacts/epic26-pr0142/debug-route.png`, `.artifacts/epic26-pr0142/menu-dom-debug.png`, `.artifacts/epic26-pr0142/seating-default-after-click.png`, `.artifacts/epic26-pr0142/seating-xlsx-after-click.png`, `.artifacts/epic26-pr0142/grouping-workspace.png`

- 2026-03-25 frontend export action cleanup:
  - `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerExportActionGroup.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/useSeatingExportFlow.spec.ts`
- 2026-03-25 local import remediation proof:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_class_list_import_examples.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/unit/web/test_apps_classroom_planner_imports.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/cli/test_smoke_seating_export_readiness.py`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/ClassroomPlannerView.spec.ts`
  - `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/components/CreateRosterModal.vue src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/useClassListImportFlow.ts`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
  - `pdm run ruff check src/skriptoteket/config.py src/skriptoteket/di/curated_apps.py src/skriptoteket/protocols/classroom_planner_imports.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/imports.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/rosters.py src/skriptoteket/infrastructure/curated_apps/apps/classroom_planner/class_list_document_extractor.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py src/skriptoteket/cli/commands/smoke_seating_export_readiness.py tests/unit/application/apps/classroom_planner/test_class_list_import_examples.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/unit/web/test_apps_classroom_planner_imports.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/cli/test_smoke_seating_export_readiness.py scripts/playwright_pr_0137_class_list_import_check.py`
  - `pdm run python -m scripts.playwright_pr_0137_class_list_import_check --base-url http://127.0.0.1:5173`
- 2026-03-25 local export runtime parity slice:
  - `pdm run pytest tests/unit/test_config.py`
  - `pdm run ruff check src/skriptoteket/config.py tests/unit/test_config.py`
  - `PYTHONPATH=src pdm run python -c "from skriptoteket.config import Settings; s=Settings(); print(s.ARTIFACTS_ROOT); print(s.VAULT_ROOT); print(s.SIR_CONVERT_A_LOT_V2_BASE_URL); print(s.SIR_CONVERT_A_LOT_V2_CALLBACK_BASE_URL)"`
  - `docker compose exec -T db pg_isready -U postgres -d skriptoteket`
  - `docker compose exec -T db psql -U postgres -d skriptoteket -c "select column_name from information_schema.columns where table_name = 'classroom_planner_plan_drafts' and column_name = 'smart_enabled';"`
  - `PYTHONPATH=src pdm run python -m skriptoteket.cli reconcile-seating-export-webhooks`
  - `BOOTSTRAP_SUPERUSER_EMAIL=superuser@local.dev PYTHONPATH=src pdm run python -m skriptoteket.cli smoke-seating-export-readiness --timeout-seconds 90 --poll-interval-seconds 2`
- 2026-03-25 PR-0145 migration integrity remediation:
  - `pdm run ruff check migrations/versions/0032_user_file_vault.py tests/integration/migration_schema_assertions.py tests/integration/migration_idempotency_support.py tests/integration/test_migration_revision_coverage_idempotent.py scripts/check_migration_test_coverage.py`
  - `pdm run python -m scripts.check_migration_test_coverage`
  - `pdm run pytest -m docker tests/integration/test_migration_revision_coverage_idempotent.py`
  - `pdm run db-upgrade`
  - `pdm run db-upgrade`
- 2026-03-25 Git-backed Hemma redeploy:
  - `ssh hemma /bin/bash <<'EOF' ... ./scripts/hemma_deploy_and_verify_seating_export.sh EOF`
  - passed with `export_job_id=b5301445-411a-47e7-9d55-2ef61f804f7e` and `pdf_bytes=9717`
  - final health snapshot:
    - `ssh hemma 'cd ~/apps/skriptoteket && git rev-parse --short HEAD && sudo docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "skriptoteket-web|skriptoteket-worker|sir_convert_a_lot_prod"'`
    - `ssh hemma 'cd ~/apps/sir-convert-a-lot && git rev-parse --short HEAD && curl -fsS http://127.0.0.1:28085/readyz'`
- 2026-03-25 packaging regression proof/fix:
  - failing clean build symptom on Hemma before `c09b17e`: `ModuleNotFoundError: No module named 'pdfplumber'`
  - local runtime-path proof after the repo fix:
    - `docker run --rm skriptoteket-web:test-fixed pdm run python -c "import pdfplumber; print(pdfplumber.__version__)"`
    - returned `0.11.9`
- 2026-03-25 smart-assignment planning docs:
  - `pdm run docs-validate`
  - `pdm run docs-validate` after resolving review findings on control inventory, checkpoint semantics, missing-history behavior, and alternate-result distinctness
- 2026-03-25 EPIC-27 approval + ST-27-01 first slice:
  - `pdm run docs-validate`
  - `pdm run db-upgrade`
  - `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`
  - `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
  - `pdm run python - <<'PY' ... PY`
  - live proof passed with new roster/template and screenshots in `.artifacts/smart-assignment-st-27-01-proof/`

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
- Host dev export smoke is passing again after the `PR-0144` config normalization and a local `reconcile-seating-export-webhooks` run, but one local devops issue remains:
  - the earlier resumable-draft blocker was local schema drift on `classroom_planner_plan_drafts.smart_enabled`; that is cleared after the 2026-03-25 reset/reseed sequence
  - the migration-integrity follow-up is now narrowed: the reproducible defect was `0032_user_file_vault` index creation on fresh upgrade, and that local fix is in the worktree; the earlier `alembic_version` error is not reproducing on current clean reruns
- `pdm.lock` still has local, uncommitted follow-up changes after the `pdfplumber` runtime fix; do not lose or silently overwrite that diff.
- `ST-26-02` and `EPIC-26` docs are still marked `ready` / unchecked even though `PR-0137` shipped; decide whether to mark them done after the lockfile follow-up and any final review closure.
- `ST-27-01` has only its first vertical slice in place; the deeper contract reset is still unfinished even though the review/ADR lane is approved.
- Local laptop Sir Convert remains an explicit CPU-only Docker debug lane; Hemma/public is the default supported upstream for Skriptoteket dev/runtime policy.
- `PR-0144` is implemented locally, but keep watching host-vs-container runtime parity when debugging export issues on `http://127.0.0.1:5173/apps/classroom.group-seating-studio`.

## Next Steps

- Start `PR-0143` next:
  - build the teacher-facing seating workbook presentation on top of the new local XLSX job lane
  - preserve `Affisch (A3)` as the default seating action while keeping `.xlsx` menu-only
- After `PR-0143`, continue the locked grouping order:
  - `PR-0139`
  - `PR-0140`
  - `PR-0141`
- Continue `ST-27-01` from the delivered smart-toggle slice:
  - remove old student-planning runtime/persistence semantics fully
  - add new smart control persistence/contracts for `Support seat`, `Keep apart`, and `Keep near`
  - keep `Use history` as a contract-only placeholder until `ST-27-02` export checkpoints land
