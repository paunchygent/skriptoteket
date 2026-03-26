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
- EPIC-26 export baseline is in place locally:
  - `PR-0139` / `PR-0140` shipped grouping export hierarchy plus local XLSX delivery
  - `PR-0141` / `PR-0146` moved grouping + seating PDFs to local WeasyPrint renderers and removed the seating-specific Sir Convert callback lane
  - `PR-0142` / `PR-0143` shipped seating XLSX with the spatial single-sheet workbook shape
  - keep using the host `dev-local` lane for real planner/export proofs; container-only logs are not enough
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
  - 2026-03-26 product-direction correction now locked in docs:
    - primary smart-rule authoring is class-wide and visual, not drawer-first per student
    - `Support seat` is dropped from the teacher-facing model and replaced with seating-only `Närmare läraren`
    - the student metadata drawer is demoted to advanced notes/history only and must not be treated as the main smart editing surface
  - PR-sliced follow-up is now documented:
    - `docs/backlog/prs/pr-0147-klassrumskartan-seating-only-teacher-distance-contract-reset.md`
    - this PR is the next recommended slice before any visual smart-rule UI work
  - post-review tightening already applied: shared-vs-mode-specific controls are now explicit, grouping checkpoints are the future primary grouping-history lane, `Use history` blocks when no eligible checkpoints exist, canonical assignment-hash semantics are defined, and `En smart variant till` now requires a distinct result or a short no-further-variant message
  - `ST-27-01` is now `in_progress` and its first delivered slices are:
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
  - remaining `ST-27-01` scope still to implement:
    - class-wide visual smart-rule authoring in the seating workspace
    - toolbar-based `Håll isär`, `Håll nära`, and seating-only `Närmare läraren`
    - explicit teacher-distance fairness/history behavior on top of export-backed checkpoints
- 2026-03-27 smart-rule interaction model is now locked in docs:
  - one active smart tool at a time in the workspace
  - `Närmare läraren` is unary click-to-toggle
  - `Håll isär` / `Håll nära` are 2+ student cluster rules authored through multi-select plus explicit commit
  - overlapping visible relationship clusters are blocked in V1
  - `Use history` remains background behavior only for now
  - next implementation task is `docs/backlog/prs/pr-0149-klassrumskartan-seating-smart-rule-toolbar-and-non-overlapping-cluster-authoring-v1.md`

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
- 2026-03-26 ST-27-01 docs-as-code correction before further smart-rule implementation:
  - updated `ADR-0074`, `EPIC-27`, `REV-EPIC-27`, `ST-27-01`, `ST-27-03`, `ST-27-04`, and the smart-assignment decision memo to lock class-wide visual rule authoring, seating-only `Närmare läraren`, and the drawer demotion
  - `pdm run docs-validate`
- 2026-03-26 ST-27-01 next PR slice planning:
  - added `PR-0147` as the contract-alignment slice for replacing `support_seat` with a seating-only teacher-distance concept across domain/API/persistence/frontend contract sync
  - `pdm run docs-validate`
- 2026-03-26 Conversion Hub boundary planning refresh:
  - updated `ADR-0066`, `EPIC-21`, `ST-21-01`, `REV-EPIC-21`, and added `PR-0148` to lock the local job-ledger/auth boundary plus same-host Unix-socket transport shape
  - `pdm run docs-validate`
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
- 2026-03-27 smart-rule interaction docs/task clarification:
  - updated `ADR-0074`, the smart-assignment decision memo, `ST-27-01`, `ST-27-03`, `ST-27-04`, `EPIC-27`, and `docs/index.md`
  - added `PR-0149` as the next implementation slice for seating smart-rule toolbar authoring with non-overlapping visible relationship clusters
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

- `http://127.0.0.1:5173/apps/classroom.group-seating-studio` currently resolves to the host `pdm run dev-local` Vite/uvicorn pair, not the Docker frontend/web ports:
  - `lsof -nP -iTCP:5173 -sTCP:LISTEN` shows host `node ... vite`
  - `lsof -nP -iTCP:8000 -sTCP:LISTEN` shows host `uvicorn ... --reload`
  - container logs can therefore look healthy while the page still fails against the host stack
- Host dev export smoke now matches the local Klassrumskartan PDF boundary:
  - seating and grouping PDFs both render locally in Skriptoteket on the host `dev-local` lane
  - the latest resumable-draft blocker was schema drift against active smart-assignment-v1 persistence, and the local worktree now carries the missing Alembic revisions plus passing idempotency checks
- `pdm.lock` still has local, uncommitted follow-up changes after the `pdfplumber` runtime fix; do not lose or silently overwrite that diff.
- `ST-26-02` and `EPIC-26` docs are still marked `ready` / unchecked even though `PR-0137` shipped; decide whether to mark them done after the lockfile follow-up and any final review closure.
- `ST-27-01` now has the contract reset implemented locally, but the class-wide visual smart-rule authoring UI is still unfinished even though the review/ADR lane is approved.
- Conversion Hub remains on the thin `PR-0064` passthrough contract:
  - no local job ledger yet
  - status/download still conceptually depend on upstream job ids
  - the next docs-first slice is `PR-0148`, which defines the local-ledger/auth boundary and same-host Unix-socket transport shape before implementation

## Next Steps

- Put the Conversion Hub docs package in front of architect review:
  - assess `ADR-0066`, `EPIC-21`, `ST-21-01`, `REV-EPIC-21`, and `PR-0148`
  - confirm the local-ledger + proxy-download + Unix-socket direction before implementation
- Continue `ST-27-01` from the delivered smart-toggle slice:
  - execute `PR-0149` as the next implementation slice for seating
  - build toolbar-based `Keep apart`, `Keep near`, and seating-only `Närmare läraren` flows instead of drawer-first student metadata editing
  - keep relation rules as non-overlapping visible clusters in V1
  - keep draft-level smart controls near the workspace/top-panel surfaces; do not add a global smart-settings drawer unless multiple stable cross-cutting toggles justify it
  - keep `Use history` as a contract-only placeholder until `ST-27-02` export checkpoints land
