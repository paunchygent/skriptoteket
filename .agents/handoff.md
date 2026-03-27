# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-27
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0120`, `PR-0121`, `PR-0122`, `PR-0123`, `PR-0124`, `PR-0125`, `PR-0126`, `PR-0137`, `PR-0138`, `PR-0139`, `PR-0140`, `PR-0142`, `PR-0143`, `PR-0145`, `PR-0146`, `PR-0147`, `PR-0148`, `PR-0151`

## Status

- Hemma is clean and Git-aligned after the reset/redeploy sequence; `sir_convert_a_lot_prod`, `skriptoteket-web`, and `skriptoteket-worker` are healthy.
- `PR-0137` shipped the class-list import remediation:
  - example corpus under `data/class_list_example_inputs/` parses across `.txt` / `.csv` / `.tsv` / `.xls` / PDF-backed fixtures and create/edit class-list flows expose in-modal `Importera från fil`
  - successful imports reconcile into overview state, edit-mode imports no longer remap student IDs by row position, and roster student-list replacement is still blocked while an active draft depends on the class list
- `PR-0138` shipped the Sir Convert runtime-policy cleanup:
  - this repo now uses only `SIR_CONVERT_A_LOT_V2_API_KEY`
  - local Skriptoteket defaults to the Hemma/public Sir Convert lane
- `PR-0144` now has a first host-runtime recovery slice in place:
  - host `Settings()` normalize container-only local defaults onto `/tmp/skriptoteket/artifacts` and `/tmp/skriptoteket/vault` when running outside Docker in development
  - host `Settings()` rewrite `SIR_CONVERT_A_LOT_V2_BASE_URL=http://host.docker.internal:8085` to `http://127.0.0.1:8085` for host-run dev processes while keeping the callback URL on `host.docker.internal:8000` for the Dockerized Sir Convert callback lane
  - after local DB/bootstrap recovery, the host-side `smoke-seating-export-readiness` passed again and produced a Vault-backed PDF from the `127.0.0.1` lane
- `PR-0145` is now implemented locally:
  - `scripts/check_migration_test_coverage.py` now enforces explicit integration coverage for all 49 Alembic revisions
  - `migrations/versions/0032_user_file_vault.py` now refreshes inspection state before index creation, so fresh upgrades keep the `user_vault_files` indexes and host `pdm run db-upgrade` reruns no-op cleanly
- EPIC-26 export baseline is in place locally:
  - `PR-0139` / `PR-0140` shipped grouping export hierarchy plus local XLSX delivery
  - `PR-0141` / `PR-0146` moved grouping + seating PDFs to local WeasyPrint renderers and removed the seating-specific Sir Convert callback lane
  - `PR-0142` / `PR-0143` shipped seating XLSX with the spatial single-sheet workbook shape
  - keep using the host `dev-local` lane for real planner/export proofs; container-only logs are not enough
- Migration guardrail added during `PR-0139`: `scripts/check_migration_test_coverage.py` now fails if Alembic has anything other than a single head, because recent operator-error incidents created split-head local states.
- Smart-assignment docs are approved and active:
  - canonical set: `docs/reference/ref-klassrumskartan-smart-assignment-v1-decision-memo-2026-03-25.md`, `docs/adr/adr-0074-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/epics/epic-27-klassrumskartan-smart-assignment-v1.md`, `docs/backlog/reviews/review-epic-27-klassrumskartan-smart-assignment-v1.md`, and `docs/backlog/stories/story-27-01-klassrumskartan-smart-assignment-contract-reset-and-control-model.md` through `story-27-05`
  - locked shape: per-mode `Smart` beside `Slumpa`, class-wide visual authoring, seating-only `Närmare läraren`, no drawer-first editing, export-only checkpoints, no legacy metadata compatibility, and grouping-specific seating-distance toggle
  - current ownership correction now locked in docs: smart rules are roster-global, draft toggles/arrangements stay draft-local, and checkpoints are history artifacts only
- `ST-27-01` is now `done` and its delivered slices are:
  - new persisted `smart_enabled` draft flag in domain/API/repository + Alembic migration `e4b7c2d9a1f0_add_smart_enabled_to_classroom_planner_drafts.py`
  - small `Smart` toggles rendered beside `Slumpa` in both grouping and seating workspaces
  - old visible notes/proximity/stability drawer no longer opens from the workspace shell
  - `PR-0147` is now implemented locally as the contract-alignment reset:
    - domain/API/frontend contract now uses `StudentSeatingPreference.near_teacher` and `seating_preferences`
    - `smart_preferences.support_seat` is rejected at the API boundary with no compatibility shim
    - repository history snapshots and ORM mapping now store `seating_preferences[].near_teacher`
    - forward Alembic revision `1d3e5f7a9b2c_reset_student_smart_preferences_to_.py` replaces `classroom_planner_student_smart_preferences` with `classroom_planner_student_seating_preferences`
    - the notes-only SPA now preserves hidden `seating_preferences` and `relationship_rules` during load/autosave instead of dropping them
  - local frontend compatibility-only prune for the contract reset is now in place:
    - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts` now treats student planning metadata as notes-only and carries `seating_preferences` / `relationship_rules` in the workspace contract
    - `frontend/apps/skriptoteket/src/views/apps/components/PlannerMetadataDrawer.vue` now exposes only teacher notes; legacy slider controls are deleted
    - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` once again opens the notes drawer from the seating workspace while grouping stays drawer-free
    - no global smart-settings surface is planned in this slice; future smart inputs should ship as local editors first, with any draft-level toggle surface deferred until multiple stable cross-cutting controls exist
- 2026-03-27 smart-rule interaction model is locked in docs: one active tool, unary `Närmare läraren`, 2+ student `Håll isär` / `Håll nära` via multi-select + explicit commit, no overlapping visible relation clusters in V1, and `Use history` background-only
- `PR-0149` is now implemented locally in the frontend worktree:
  - seating has a visible smart-rule surface with one active tool at a time
  - `Närmare läraren` toggles through the shared seating store instead of the notes drawer path
  - `Håll isär` / `Håll nära` use temporary multi-select plus explicit `Skapa regel`
  - overlapping visible relationship clusters are blocked client-side with teacher-facing feedback
  - the seating pool/canvas now show pending selections and lightweight tile markers, while the drawer stays secondary
  - ruthless review fixes already applied: autosave now preserves the active smart tool, and relationship-rule deletion now respects workspace-busy guards with matching disabled summary actions
- `PR-0151` is now done with review remediation and backend hardening in place:
  - smart rules moved out of draft workspace/domain persistence and into new roster-owned aggregates, handlers, API routes, ORM models, repository seams, and Alembic revision `5f2c7d1a9b8e_move_classroom_planner_smart_rules_to_.py`
  - draft PATCH/workspace contracts now carry only draft-local arrangement state, notes, and run controls; roster smart rules load/save through `/rosters/{roster_id}/smart-rules`
  - the frontend store now loads roster smart rules separately, autosaves them through the roster endpoint, and no longer blocks authoring when draft-level `Smart` is off
  - review remediation now adds roster-rule optimistic concurrency, split autosave-lane retry safety, fail-safe workspace hydration, a shared owner-scoped export-workspace hydrator for grouping/seating exports, and startup schema-shape verification
  - forward repair migration `7d4c1a2b9e6f_repair_roster_smart_rule_root_contract.py` now heals the impossible local/Docker drift state where Alembic was at head but `classroom_planner_roster_smart_rule_sets` was missing and child FKs still pointed at `classroom_planner_rosters`
  - Docker dev commands now auto-run the in-container `pdm run db-upgrade` path via `pdm run dev-db-upgrade`, and `.agents/rules/054-alembic-migrations.md` now explicitly treats applied migrations as immutable
  - the latest frontend reviewer follow-ups are also fixed locally: `clearWorkspace()` now invalidates stale in-flight workspace loads, and late autosave responses are ignored after clear/exit so they cannot repopulate planner state
- `PR-0148` is now done as the Conversion Hub ownership/auth boundary cutover:
  - new local `conversion_hub_jobs` ledger maps owner, local job id, upstream job id, formats, status, correlation, and optional PDF layout metadata
  - Conversion Hub submit/status/download now use local UUID job ids at the product boundary; upstream Sir Convert ids stay internal
  - invalid `job_spec` payloads are rejected before local job creation, status refresh is owner-gated and poll-on-read, and artifact download stays proxied through Skriptoteket instead of redirecting upstream
  - same-host Sir Convert transport now supports Unix sockets first with `127.0.0.1` HTTP fallback via `SIR_CONVERT_A_LOT_V2_UNIX_SOCKET_PATH`
  - unknown upstream statuses now surface as controlled service errors, and the live route proof on `http://127.0.0.1:5173` still passes with the tightened `wait_seconds <= 20` contract

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
- 2026-03-26 PR-0141 / PR-0146 local PDF boundary:
  - grouping + seating PDFs now render locally in Skriptoteket via WeasyPrint, and the seating-specific Sir Convert callback lane is deleted
  - host proofs/artifacts remain under `.artifacts/epic26-pr0141-host-check/`, `.artifacts/epic26-root-cause-seating/`, and `.artifacts/epic26-pr0141-seating-branding-check/`
- 2026-03-26 ST-27-01 frontend compatibility-only prune:
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`
  - `pdm run fe-type-check`
  - live proof against the dev SPA:
    - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
    - artifact: `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
    - the smoke script was updated to keep the seating proof on current zoom/drawer behavior instead of failing early on a stale drag/drop seat-assignment assumption
- 2026-03-27 PR-0148 Conversion Hub local job ledger + owned status/download boundary:
  - `pdm run db-upgrade`
  - `pdm run pytest tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/web/conversion_hub/test_apps_conversion_hub_job_spec.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py`
  - `pdm run python -m scripts.check_migration_test_coverage`
  - `pdm run pytest -o addopts='' 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[2b6c4d8e1f9a]'`
  - `pdm run mypy src/skriptoteket/application/curated_apps/conversion_hub.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py src/skriptoteket/protocols/conversion_hub.py src/skriptoteket/infrastructure/db/models/conversion_hub_job.py src/skriptoteket/infrastructure/repositories/conversion_hub_jobs.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py src/skriptoteket/web/api/v1/apps_conversion_hub.py src/skriptoteket/di/curated_apps.py`
  - `pdm run ruff check src/skriptoteket/application/curated_apps/conversion_hub.py src/skriptoteket/application/curated_apps/handlers/conversion_hub_jobs.py src/skriptoteket/protocols/conversion_hub.py src/skriptoteket/infrastructure/db/models/conversion_hub_job.py src/skriptoteket/infrastructure/repositories/conversion_hub_jobs.py src/skriptoteket/infrastructure/curated_apps/apps/conversion_hub/sir_convert_client_v2.py src/skriptoteket/web/api/v1/apps_conversion_hub.py src/skriptoteket/di/curated_apps.py tests/unit/application/curated_apps/handlers/test_conversion_hub_jobs.py tests/unit/web/conversion_hub/test_apps_conversion_hub_api.py tests/unit/infrastructure/curated_apps/apps/conversion_hub/test_sir_convert_client_v2.py tests/integration/migration_schema_assertions.py`
  - `pdm run docs-validate`
  - live proof against `http://127.0.0.1:5173` via bootstrap-superuser API script:
    - malformed `pdf_layout` + `md` request returned `422` with `VALIDATION_ERROR` before handler-owned job creation
    - submit/status/download still succeeded with local job id `170e915b-79b0-4104-a64a-8b266e4793cc`; artifacts: `.artifacts/pr0148-live-check/invalid.json`, `.artifacts/pr0148-live-check/submit.json`, `.artifacts/pr0148-live-check/status.json`, `.artifacts/pr0148-live-check/artifact.md`
- 2026-03-26 PR-0147 seating-only teacher-distance contract reset:
  - `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q`
  - `pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py -q`
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py -q`
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run pytest tests/integration/test_migration_revision_coverage_idempotent.py -m docker -q -k 1d3e5f7a9b2c`
  - `pdm run docs-validate`
  - `pdm run db-upgrade`
  - live proof against `http://127.0.0.1:5173`:
    - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
    - artifact: `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
  - runtime note:
    - the observed planner `500` on `5173` was local DB schema drift during the live check; upgrading the local DB to head fixed it and the reused planner smoke then passed
- 2026-03-27 smart-rule docs/task clarification: updated `ADR-0074`, the smart-assignment decision memo, `ST-27-01`, `ST-27-03`, `ST-27-04`, `EPIC-27`, and `docs/index.md`; added `PR-0149` for seating smart-rule toolbar authoring with non-overlapping visible relationship clusters
- 2026-03-27 PR-0149 seating smart-rule toolbar + non-overlapping cluster authoring:
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/components/RoomCanvas.spec.ts`
  - `pdm run fe-type-check`
  - live proof against `http://127.0.0.1:5173`:
    - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
    - artifact: `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
  - ruthless review follow-up verification:
    - added red/green coverage for autosave tool stickiness and busy-state deletion gating, reran the full PR-0149 frontend target set plus `pdm run fe-type-check`, and confirmed the reused smoke on immediate rerun after one existing grouping-history cleanup assertion failure in `scripts.playwright_classroom_planner_smoke.py`
- 2026-03-27 smart-rule ownership correction before further backend code:
  - updated `ADR-0074`, `ST-27-01`, `ST-27-02`, `ST-27-03`, `PR-0147`, `PR-0149`, `PR-0150`, and `docs/index.md`
  - added `PR-0151` for roster-global smart-rule ownership and draft-local arrangement boundary reset
  - refined `PR-0150` so checkpoints are roster-scoped history artifacts that depend on `PR-0151` and do not own smart rules
  - tightened `PR-0151` into the exact execution plan, including explicit frontend retargeting of the current local `PR-0149` toolbar/store work
  - added a landing note to `PR-0149` so it is not mistaken for merge-ready before the ownership reset
  - `pdm run docs-validate`
- 2026-03-27 PR-0151 roster-global smart rules and draft-local arrangement reset:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rules.py tests/unit/web/apps/classroom_planner/test_smart_rules_api.py tests/unit/infrastructure/repositories/test_classroom_planner_smart_rules.py tests/unit/application/apps/classroom_planner/test_grouping_exports.py tests/unit/application/apps/classroom_planner/test_seating_exports.py tests/unit/web/test_startup_checks.py -q`
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
  - `pdm run fe-type-check`
  - `pdm run typecheck`
  - `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[5f2c7d1a9b8e]' -q`
  - `pdm run pytest tests/unit/web/test_startup_checks.py -q`
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_grouping_exports.py tests/unit/application/apps/classroom_planner/test_seating_exports.py -q`
  - `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[7d4c1a2b9e6f]' -q`
  - `pdm run db-upgrade`
  - `pdm run dev-db-upgrade`
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/classroomPlannerRouteShellSaveGuards.spec.ts`
  - live backend proof on the current host stack via one-off bootstrap-superuser API script:
    - `http://127.0.0.1:8000/healthz` returned `200`
    - `GET /api/v1/apps/classroom.group-seating-studio/drafts/grouping/61951fc7-924b-41c5-9916-82b180416142/exports/jobs/recover` returned `200` with `null` instead of `500`
  - live Docker planner proof on `http://127.0.0.1:5173`:
    - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
    - artifact: `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
  - `pdm run docs-validate`
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

- Host dev export smoke now matches the local Klassrumskartan PDF boundary:
  - seating and grouping PDFs both render locally in Skriptoteket on the host `dev-local` lane
  - the latest resumable-draft blocker was schema drift against active smart-assignment-v1 persistence, and the local worktree now carries the missing Alembic revisions plus passing idempotency checks
- `pdm.lock` still has local, uncommitted follow-up changes after the `pdfplumber` runtime fix; do not lose or silently overwrite that diff.
- `ST-26-02` and `EPIC-26` docs are still marked `ready` / unchecked even though `PR-0137` shipped; decide whether to mark them done after the lockfile follow-up and any final review closure.
- `ST-27-01` now has both the seating contract reset (`PR-0147`) and the first visual seating smart-rule authoring slice (`PR-0149`) implemented locally, but the docs now also say the current draft-owned rule persistence must be corrected before more smart-assignment backend work lands.
- `PR-0151` review remediation, Docker drift repair, and the related export/runtime hardening are now implemented locally and have a passing live planner smoke on `5173`; keep the new `7d4c1a2b9e6f` repair migration in mind if another long-lived dev DB reports Alembic head but misses the roster smart-rule root contract.
  - the revision-0 false-conflict follow-up is now fixed locally: repaired/backfilled smart-rule roots at revision `0` can advance to revision `1` on the first edit instead of raising `Expected 0, got 0`
- Conversion Hub now has a local job ledger and closed docs for `PR-0148`; the route enforces Sir Convert's real `wait_seconds <= 20` limit, so keep that contract in sync if the upstream service changes.
## Next Steps

- Continue the smart-assignment lane in the corrected order:
  - execute `PR-0150` next for seating checkpoint registry + normalized assignment-hash dedupe under `ST-27-02`
  - keep relation rules as non-overlapping visible clusters in V1
  - keep draft-level smart controls near the workspace/top-panel surfaces; do not add a global smart-settings drawer unless multiple stable cross-cutting toggles justify it
