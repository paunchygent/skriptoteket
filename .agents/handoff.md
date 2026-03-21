# Session Handoff

Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-21
- Branch: `main` + local changes
- Current sprint: N/A (no sprints)
- Production: Full Vue SPA
- Completed: `ST-24-01` implemented locally across `PR-0079` to `PR-0081`; landing page fundamentals, explicit resume, and safe asset delete now match the narrowed teacher-first direction.

## Current Session (2026-03-21)

- Klassrumskartan fundamentals rollback / UX repair:
  - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`: default lesson mode now auto-selects from bootstrap so class + classroom is enough to open the planner.
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSelectionGate.vue`: removed dead promo/start cards, made roster/template cards selectable as full cards, surfaced simple capacity text, and kept the gate focused on choosing class + room.
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`: stripped the always-visible advanced controls from the default workspace, kept `Slumpa`, and moved the teacher drawer behind an explicit `Placeringprofil` action.
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerMetadataDrawer.vue`: reduced the visible model to teacher-authored placement observations; removed pair-constraint UI and zone-preference UI from the current teacher surface.
  - `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.vue` and `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`: fixed oversized modal behavior with viewport-bounded dialogs, scrollable bodies, sticky footers, and outside-click close via a dedicated backdrop target.
- ST-24-01 implementation:
  - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`: landing page is now always the default first screen; start-planning uses server-backed resolve; auto-resume on mount is removed; explicit resumable CTA data is loaded from the backend.
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSelectionGate.vue`: default-surface lesson mode is gone; planner launch depends on selected class + classroom only; explicit `Fortsätt senaste utkastet` CTA is rendered on the landing page.
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` and `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`: removed the legacy draft session key / direct-create path, added `resolveDraft()`, `getResumableDraft()`, and `abandonDraft()`, and made `Byt klass / rum` retire the server-side draft instead of only clearing local state.
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`, `src/skriptoteket/infrastructure/repositories/classroom_planner.py`, `src/skriptoteket/protocols/classroom_planner.py`, and `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`: added draft lifecycle fields (`status`, `last_opened_at`), removed `CreateDraftHandler`, added `ResolveDraftHandler` + `AbandonDraftHandler`, enforced one active draft per owner, and added owner-scoped lifecycle locking so resolve cannot duplicate active drafts under overlap.
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/rosters.py` and `src/skriptoteket/application/curated_apps/classroom_planner/handlers/templates.py`: block delete when an active draft depends on the asset and return a teacher-readable conflict.
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/planning.py` and `src/skriptoteket/web/api/v1/apps_classroom_planner.py`: mutating planner flows now reject inactive drafts; `POST /drafts` is removed; the public lifecycle contract is `POST /drafts/resolve`, `GET /drafts/resumable`, and `POST /drafts/{id}/abandon`.
  - `migrations/versions/c2a6b2f4d91e_classroom_planner_draft_lifecycle_and_.py` and `migrations/versions/d8f0d0ef2b6d_classroom_planner_single_active_draft_.py`: add lifecycle fields plus a partial unique index enforcing at most one active planner draft per owner, with migration-time dedupe of older active drafts.
  - Added focused tests:
    - `tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py`
    - `tests/unit/application/apps/classroom_planner/test_asset_delete_guards.py`
    - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts`
    - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSelectionGate.spec.ts`
    - `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.spec.ts`
    - `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.spec.ts`
- Important product note:
  - User explicitly rejected the earlier “show everything” Slice 2 UX. Continue with docs-as-code and add visible features one at a time only after agreement on meaning, precedence, and teacher-facing language.
- Backlog planning rewrite:
  - Rewrote `docs/backlog/epics/epic-24-group-seating-studio-slice-2.md` as a fundamentals-recovery epic.
  - Added `ST-24-01` to `ST-24-04` covering landing-page fundamentals, class-first workspace + draft entry, grouping fundamentals + saved groupings, and seating fundamentals + saved seating arrangements.
  - Added `docs/adr/adr-0071-group-seating-studio-fundamentals-workflow-and-saved-artifacts.md` to lock the fundamentals-first workflow contract and updated it to point at the class-first refinement.
  - Enriched `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md` with the user review’s architectural guidance so the review now records the UX/state reset, draft lifecycle reset, and saved-output model reset rather than implying a domain reset.
  - Added `docs/prd/prd-group-seating-studio-v0.3.md` as the current class-first product direction for Klassrumskartan, kept `v0.2` as superseded, and added `docs/reference/ref-group-seating-studio-product-direction-2026-03-21.md` as the concise product-direction note.
  - Added `docs/adr/adr-0072-group-seating-studio-class-first-workspace-and-draft-kinds.md` to lock the class-first hierarchy: class as anchor, classroom as secondary context, separate seating/grouping draft kinds, one active draft per class per kind, and class-owned history.
  - Updated `docs/adr/adr-0069-group-seating-studio-domain-model.md` to clarify that the normalized persistence core remains valid while ADR-0072 refines the teacher-facing draft model, and marked `docs/adr/adr-0070-group-seating-studio-slice-2-engine-and-snapshots.md` as superseded by ADR-0071/ADR-0072.
  - Added `PR-0079`, `PR-0080`, and `PR-0081` under `docs/backlog/prs/` to split `ST-24-01` into concrete implementation slices for landing-page UI/start contract, draft resolve + explicit resume, and safe asset delete + modal hardening.
  - Updated `docs/index.md` to include the new PRD v0.3, ADR-0072, the class-first `ST-24-02` story path, and the new product-direction reference note.
- Remediation backlog gate for code alignment:
  - Added `docs/backlog/stories/story-24-05-group-seating-studio-codebase-realignment-and-superseded-contract-removal.md` as the active EPIC-24 remediation story.
  - Added `PR-0082` to `PR-0085` under `docs/backlog/prs/` to remove visible legacy planner surfaces, prune frontend store/type contract drift, remove superseded backend/domain contracts, and replace the owner-global draft invariant with class-scoped draft kinds.
  - Updated `EPIC-24` so `ST-24-05` is the active remediation gate before `ST-24-02` to `ST-24-04`.
  - Updated `ST-24-02`, `ST-24-03`, and `ST-24-04` notes so developers treat the remediation gate as a prerequisite instead of assuming the current code is already a clean foundation.

## Previous Sessions

- Earlier Slice 1 history remains in `.agents/readme-first.md` and the EPIC-23 docs/review trail.

## Verification

- 2026-03-21: `pdm run docs-validate` (PASSED).
- 2026-03-21: `pdm run docs-validate` after ADR-0071 + EPIC-24/review/story refinements + `PRD-group-seating-studio-v0.2` + `PR-0078` (PASSED).
- 2026-03-21: `pdm run docs-validate` after PRD v0.3 + ADR-0072 + EPIC-24/story/PR rewrites for the class-first workspace direction (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts` (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-21: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_asset_delete_guards.py -q` (PASSED).
- 2026-03-21: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/apps/classroom_planner/test_asset_delete_guards.py -q` after lifecycle hardening (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/components/CreateRosterModal.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/useClassroomState.spec.ts` (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` after ST-24-01 implementation (PASSED).
- 2026-03-21: `pdm run pytest tests/integration/database/test_classroom_planner_migration.py -q -m 'integration and docker'` (PASSED).
- 2026-03-21: `pdm run ruff check src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/protocols/classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/rosters.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/templates.py src/skriptoteket/di/curated_apps.py src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_asset_delete_guards.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/web/apps/classroom_planner/test_api.py` (PASSED).
- 2026-03-21: `pdm run db-upgrade` against the local dev DB after the new draft-lifecycle migration was added (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa build` after removing the legacy draft-create path and session-key flow (PASSED).
- 2026-03-21: `pdm run python - <<'PY' ...` local Playwright/request smoke against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` using the bootstrap superuser after `pdm run db-upgrade` (PASSED). Verified:
  - landing page opens first
  - select class + classroom and open the planner
  - `Byt klass / rum` abandons the active draft instead of leaving it active
  - `GET /drafts/resumable` returns `null` after reset
  - the landing page no longer shows `Fortsätt senaste utkastet` after abandon/reset
  - deleting the same class and classroom now succeeds after the draft is abandoned
  - screenshots saved under `.artifacts/st-24-01-draft-lifecycle-check/`
- 2026-03-21: `pdm run python - <<'PY' ...` local Playwright/request smoke against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` using the bootstrap superuser (PASSED). Verified:
  - landing page opens first
  - `Fortsätt senaste utkastet` appears instead of planner hijack
  - `Lektionsläge` is absent from the default landing flow
  - selecting one class + one classroom enables `Öppna planeringen`
  - `Byt klass / rum` returns to the landing page
  - delete is blocked for both class and classroom when an active draft depends on them
  - screenshots saved under `.artifacts/st-24-01-live-check/`
- 2026-03-21: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local` + headless local browser checks (PARTIAL/PASSED where noted):
  - planner entry smoke PASSED: selected seeded class + room, opened planner, and confirmed the default workspace no longer shows `Elevmetadata i regelmotor` or `Historikregler`, while `Placeringprofil` is present.
  - class/classroom modal smoke PASSED: opened `Redigera klasslista` and `Redigera klassrum`, verified `Spara klassrum` is reachable, and confirmed outside-corner clicks close both dialogs after the dedicated backdrop fix.
- 2026-03-20: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts` (PASSED).
- 2026-03-20: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-20: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-20: `python -m py_compile src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/planning.py src/skriptoteket/infrastructure/repositories/classroom_planner.py` (PASSED).
- 2026-03-20: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q` (PASSED).
- 2026-03-20: `pdm run pytest tests/unit/application/apps/classroom_planner/test_services.py -q` (PASSED).
- 2026-03-20: `pdm run pytest tests/integration/database/test_classroom_planner_migration.py -q -m 'integration and docker'` (PASSED).
- 2026-03-20: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local` + Playwright/request smoke (PASSED): created roster/template with fixtures, opened `/apps/classroom.group-seating-studio`, selected lesson mode/assets, ran `Slumpa`, opened student metadata, fetched/applied suggestions, finalized snapshot.
- 2026-03-20: `ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local` + edit-surface smoke (PASSED): opened `Redigera klasslista` and `Redigera klassrum` from the selection gate.

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit
pnpm -C frontend --filter @skriptoteket/spa build
pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q
pdm run pytest tests/unit/application/apps/classroom_planner/test_services.py -q
pdm run pytest tests/integration/database/test_classroom_planner_migration.py -q -m 'integration and docker'
```

## Known Issues / Risks

- The backend Slice 2 APIs still exist behind the UI, but the user has explicitly asked for a much narrower, teacher-first feature rollout before exposing more of them.
- Broader repo-wide lint/typecheck/test suites have still not been rerun after the ST-24-01 implementation slice.
- The ad hoc live smokes created several dev-only roster/template rows in the local database; they are harmless but noisy.
- `PlannerWorkspaceShell.vue` still uses local tab state (`Gruppvy` / `Sittplatser`) rather than route-level mode separation; that belongs to `ST-24-02`.

## Next Steps

- Start `ST-24-05` before any new Klassrumskartan feature work; remove superseded planner contracts first.
- Keep future work fundamentals-only: route-level mode separation, no new visible advanced semantics, and no blended grouping/seating surfaces.
- Treat validation/suggestions/snapshots/pair rules/zone rules as hidden backend groundwork until each concept is explicitly approved and named.
