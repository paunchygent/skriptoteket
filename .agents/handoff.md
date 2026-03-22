# Session Handoff
Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-22
- Branch: `main` + local changes
- Current sprint: N/A (no sprints)
- Production: Full Vue SPA
- Completed: `ST-24-01` (`PR-0079` to `PR-0081`), `ST-24-05` (`PR-0082` to `PR-0085`), and `ST-24-02` (`PR-0086` to `PR-0089`) are on `main`. `ST-24-03` is now replanned locally through `PR-0090` to `PR-0093` around draft history instead of saved artifacts.
## Current Session (2026-03-22)

- `docs/backlog/stories/story-24-03-group-seating-studio-grouping-fundamentals-and-saved-groupings.md`, `docs/backlog/stories/story-24-04-group-seating-studio-seating-fundamentals-and-saved-arrangements.md`, `docs/backlog/epics/epic-24-group-seating-studio-slice-2.md`, `docs/prd/prd-group-seating-studio-v0.3.md`, `docs/adr/adr-0071-group-seating-studio-fundamentals-workflow-and-saved-artifacts.md`, `docs/adr/adr-0072-group-seating-studio-class-first-workspace-and-draft-kinds.md`, `docs/reference/ref-group-seating-studio-product-direction-2026-03-21.md`, `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md`, `docs/backlog/prs/pr-0090-klassrumskartan-grouping-draft-history-contract.md`, `docs/backlog/prs/pr-0091-klassrumskartan-grouping-workspace-fundamentals.md`, `docs/backlog/prs/pr-0092-klassrumskartan-grouping-undo-redo-and-autosave-ux.md`, `docs/backlog/prs/pr-0093-klassrumskartan-grouping-class-history-and-draft-continuity.md`, and `docs/index.md`: replanned the grouping/seating track around the simpler approved model: one active draft, bounded undo/redo history inside that draft, autosave as working-state persistence, and later export as the durable file-vault action. Removed the earlier saved-artifact/vault assumptions from the story chain before implementation starts.
- Klassrumskartan fundamentals rollback / UX repair:
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`, `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`, `src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py`, `migrations/versions/91f6c4a7b2d1_allow_roomless_seating_drafts.py`, and `scripts/playwright_classroom_planner_smoke.py`: tightened `PR-0088`/`PR-0089` around the latest product decisions. Overview, grouping, and seating now share one fixed top-panel layout so the toggle stays in the same place and size, the planner shell uses compact save/help indicators instead of oversized panels, `Avsluta` leaves the class view back to the landing surface, explicit draft discard remains the landing CTA, and seating drafts can now exist without a classroom until the teacher assigns or switches room inside the seating workspace.
  - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerSelectionGate.vue`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerClassWorkspace.vue`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerHistoryDrawer.vue`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`, and `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`: `PR-0087` is on `main`, and `PR-0088` plus `PR-0089` are implemented locally; the app is class-first at the root, the class workspace now opens neutrally with a compact task selector, grouping defaults to classroom-agnostic start with an explicit classroom-aware opt-in inside the focused grouping surface, seating keeps classroom selection inside the focused seating surface, the planner toggle returns to overview while `Avsluta` leaves back to the landing surface, explicit discard is separate on the landing CTA, and grouping/seating history is read-only and tucked into separate drawers.
  - `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`, `src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_summary.py`, `src/skriptoteket/protocols/classroom_planner.py`, `src/skriptoteket/infrastructure/repositories/classroom_planner.py`, `src/skriptoteket/web/api/v1/apps_classroom_planner.py`, `src/skriptoteket/web/api/v1/apps_classroom_planner_summary.py`, and `src/skriptoteket/di/curated_apps.py`: `PR-0086` is now implemented locally; the backend exposes a compact class-workspace summary with explicit `TaskEntryOption` rules, separate active grouping/seating summaries, and separate grouping/seating history without inflating the contract with template catalogs or reviving owner-global draft semantics.
  - Added focused coverage for `PR-0086` in `tests/unit/application/apps/classroom_planner/test_class_workspace_summary.py`, `tests/unit/web/apps/classroom_planner/test_class_workspace_summary_api.py`, and `tests/integration/infrastructure/repositories/test_classroom_planner_repository.py` to verify roster ownership, summary serialization, task-separated history ordering, template labels, and roster scoping against the real SQLAlchemy repository.
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`, `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`, and `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStoreMutations.ts`: `PR-0083` is now implemented locally; the active frontend planner contract no longer carries lesson modes, planning profiles, pair constraints, validation findings, suggestions, snapshots, or their related store methods/payload fields, and the remaining workspace DTO/store surface is fundamentals-only.
  - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`, `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.spec.ts`, `frontend/apps/skriptoteket/src/views/apps/components/PlannerSelectionGate.spec.ts`, and `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`: the obsolete classroom-planner bootstrap round-trip is removed from the SPA entry flow, resumable draft fixtures match the reduced draft contract, and the store specs now assert that `resolveDraft()` and autosave no longer send removed planner-era fields.
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`: stripped the visible legacy planner entry points from the default workspace and made the student drawer seating-only instead of a shared shell control.
  - `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue`, `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`, and `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue`: removed opposite-axis leakage from the default grouping/seating surfaces, deleted `PlannerSuggestionsPanel.vue`, and moved the static room-grid styling out of inline strings into component CSS.
  - `frontend/apps/skriptoteket/src/views/apps/components/CreateRosterModal.vue` and `frontend/apps/skriptoteket/src/views/apps/components/CreateRoomTemplateModal.vue`: fixed oversized modal behavior with viewport-bounded dialogs, scrollable bodies, sticky footers, and outside-click close via a dedicated backdrop target.
  - Added focused frontend coverage for `PR-0082` in `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`, `frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.spec.ts`, and `frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.spec.ts`.
  - `AGENTS.md`, `.agents/rules/075-browser-automation.md`, and `.claude/skills/playwright-testing/SKILL.md`: Playwright process now explicitly requires loading the Playwright skill first; the “inspect older scripts first” guidance lives in the Playwright skill/rule layer instead of `AGENTS.md`.
  - `src/skriptoteket/web/api/v1/apps_classroom_planner.py`, `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`, `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`, `src/skriptoteket/infrastructure/repositories/classroom_planner.py`, `src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py`, `src/skriptoteket/protocols/classroom_planner.py`, and `src/skriptoteket/di/curated_apps.py`: `PR-0084` is now implemented locally; the active backend contract no longer exposes lesson-mode bootstrap, validate/suggestions/apply/finalize/snapshots, or the superseded whole-workspace randomize API, and the remaining domain/persistence surface is fundamentals-only.
  - `migrations/versions/9f1a6c4d2e7b_classroom_planner_prune_superseded_.py`: drops superseded planner tables/columns and removes `independent_focus_support` while retaining the still-meaningful teacher metadata concepts (`teacher_proximity`, `stability_preference`, `preferred_zone`, `avoid_zone`).
  - `scripts/playwright_classroom_planner_smoke.py`: added a reusable repo-pattern Playwright smoke for Klassrumskartan that reuses the existing launch/login helpers, enters through the protected app route, creates a real roster/template via UI, and opens the planner workspace so future PR-specific checks can extend a stable app-specific baseline instead of guessing the setup flow again.
  - `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`, `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`, `src/skriptoteket/infrastructure/repositories/classroom_planner.py`, `src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py`, `src/skriptoteket/protocols/classroom_planner.py`, `src/skriptoteket/web/api/v1/apps_classroom_planner.py`, `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`, and `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`: `PR-0085` is now implemented locally; active drafts are class-scoped by draft kind, `draft_kind` is part of the active contract, seating drafts remain classroom-bound, grouping drafts are classroom-optional, and the current SPA launcher now uses the transitional seating-draft path explicitly.
  - `migrations/versions/6b44e9b5d3c1_classroom_planner_draft_kind_and_.py` and `scripts/classroom_planner_draft_kind_api_smoke.py`: added the class-scoped draft-kind migration plus a request-level live smoke that proves seating and grouping drafts can coexist per class/kind without reviving the owner-global invariant.
  - `docs/backlog/stories/story-24-02-group-seating-studio-class-first-workspace.md`: tightened the future class-first workspace contract so leaving the planner back to the class workspace without implicit discard is now explicit story scope instead of only ADR guidance.
- ST-24-01 implementation:
  - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue`: landing page is now always the default first screen; start-planning uses server-backed resolve; auto-resume on mount is removed; explicit resumable CTA data is loaded from the backend.
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSelectionGate.vue`: default-surface lesson mode is gone; planner launch depends on selected class + classroom only; explicit `Fortsätt senaste utkastet` CTA is rendered on the landing page.
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` and `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`: removed the legacy draft session key / direct-create path, added `resolveDraft()`, `getResumableDraft()`, and `abandonDraft()`, and made `Byt klass / rum` retire the server-side draft instead of only clearing local state.
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`, `src/skriptoteket/infrastructure/repositories/classroom_planner.py`, `src/skriptoteket/protocols/classroom_planner.py`, and `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`: the original landing-page recovery slice introduced `ResolveDraftHandler` + `AbandonDraftHandler`; `PR-0085` later replaced the old owner-global invariant with class-scoped draft kinds.
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
- Backlog planning rewrite:
  - Rewrote `docs/backlog/epics/epic-24-group-seating-studio-slice-2.md` as a fundamentals-recovery epic.
  - Added `ST-24-01` to `ST-24-04` covering landing-page fundamentals, class-first workspace + draft entry, grouping fundamentals + draft history, and seating fundamentals + draft history.
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

## Verification

- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/useClassroomState.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerTopPanel.vue src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa build`; `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_class_workspace_summary.py tests/unit/web/apps/classroom_planner/test_class_workspace_summary_api.py tests/integration/database/test_classroom_planner_migration.py -q`; `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`; `pdm run ruff check scripts/playwright_classroom_planner_smoke.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_class_workspace_summary.py tests/unit/web/apps/classroom_planner/test_class_workspace_summary_api.py tests/integration/database/test_classroom_planner_migration.py`; `pdm run db-upgrade`; `pdm run docs-validate`; `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` after the fixed top-panel / roomless-seating alignment work and the final ruthless review fixes (PASSED). Verified:
  - overview, grouping, and seating share the same top selector placement
  - grouping keeps its classroom-aware opt-in inside the live grouping workspace instead of forcing it from the class overview
  - selecting seating opens the workspace directly, then room selection happens inside it
  - the seating draft can be created without a classroom after the DB migration and room switching stays on the same active seating draft without creating history clutter
  - `Avsluta` returns to the landing surface while the draft becomes resumable there
  - the landing `Avsluta utkast` CTA can discard that resumable draft
  - screenshot saved under `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/useClassroomState.ts src/views/apps/classroomPlannerTypes.ts src/views/apps/components/PlannerSelectionGate.vue src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/components/PlannerHistoryDrawer.vue src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa build`; `pdm run ruff check scripts/playwright_classroom_planner_smoke.py`; `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` after `PR-0087` to `PR-0089` class-first workspace changes (PASSED). Verified:
  - landing shows the top-level resumable CTA before class selection
  - selecting a class opens a neutral class workspace with a compact task selector instead of jumping straight into the planner
  - grouping setup lives inside the focused grouping surface, while seating room selection lives inside the focused seating surface
  - grouping history and seating history are separate, hidden by default, and open through separate read-only drawers
  - returning from the planner keeps the active seating draft in the class workspace, and explicit discard removes it again
  - screenshot saved under `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
- 2026-03-21: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_summary.py src/skriptoteket/di/curated_apps.py src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/protocols/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_summary.py tests/unit/application/apps/classroom_planner/test_class_workspace_summary.py tests/unit/web/apps/classroom_planner/test_class_workspace_summary_api.py tests/integration/infrastructure/repositories/test_classroom_planner_repository.py`; `pdm run mypy src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_summary.py src/skriptoteket/protocols/classroom_planner.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_summary.py src/skriptoteket/di/curated_apps.py`; `pdm run pytest tests/unit/application/apps/classroom_planner/test_class_workspace_summary.py tests/unit/web/apps/classroom_planner/test_class_workspace_summary_api.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q`; `pdm run pytest tests/integration/infrastructure/repositories/test_classroom_planner_repository.py -q` after `PR-0086` class-workspace summary contract work (PASSED).
- 2026-03-21: `pdm run skills-validate` after tightening the repo-local `playwright-testing` skill workflow (PASSED).
- 2026-03-21: `pdm run docs-validate` after the Playwright rule/skill + `AGENTS.md` cleanup (PASSED).
- 2026-03-21: `pdm run docs-validate` after ADR-0071 + EPIC-24/review/story refinements + `PRD-group-seating-studio-v0.2` + `PR-0078` (PASSED).
- 2026-03-21: `pdm run docs-validate` after PRD v0.3 + ADR-0072 + EPIC-24/story/PR rewrites for the class-first workspace direction (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/useClassroomState.spec.ts` (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` after `PR-0082` frontend cleanup (PASSED).
- 2026-03-21: `pdm run fe-lint` after `PR-0082` frontend cleanup (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/useClassroomState.spec.ts` after `PR-0083` contract cleanup (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` after `PR-0083` contract cleanup (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa build` after `PR-0083` contract cleanup (PASSED).
- 2026-03-21: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py` after `PR-0084` backend pruning (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/useClassroomState.spec.ts` after `PR-0084` backend pruning (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` after `PR-0084` backend pruning (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa build` after `PR-0084` backend pruning (PASSED).
- 2026-03-21: `pdm run pytest -m 'integration and docker' tests/integration/database/test_classroom_planner_migration.py` after `PR-0084` migration changes (PASSED).
- 2026-03-21: `pdm run ruff check src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner src/skriptoteket/domain/curated_apps/classroom_planner src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py src/skriptoteket/di/curated_apps.py src/skriptoteket/protocols/classroom_planner.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/integration/database/test_classroom_planner_migration.py scripts/playwright_classroom_planner_smoke.py` after `PR-0084` backend pruning (PASSED).
- 2026-03-21: `pdm run db-upgrade` against the local dev DB after adding `9f1a6c4d2e7b_classroom_planner_prune_superseded_.py` (PASSED).
- 2026-03-21: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` after loading the Playwright skill and checking existing repo scripts (`scripts/_playwright_config.py`, `scripts/playwright_ui_smoke.py`, `scripts/playwright_st_11_09_curated_app_e2e.py`, `scripts/playwright_ui_runtime_smoke.py`, `scripts/playwright_nav_transitions_smoke.py`) (PASSED). Verified:
  - login works through the protected Klassrumskartan app route
  - a real roster and classroom can still be created and opened into the planner
  - grouping and seating workspace entry points render
  - student metadata drawer opens from the seating surface
  - screenshot saved under `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
- 2026-03-21: `pdm run docs-validate` after tightening `ST-24-02` planner-leave semantics and marking `PR-0084` done (PASSED).
- 2026-03-21: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/web/apps/classroom_planner/test_api.py -q` after `PR-0085` draft-kind lifecycle changes (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts` after `PR-0085` frontend contract adaptation (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` after `PR-0085` frontend contract adaptation (PASSED).
- 2026-03-21: `pnpm -C frontend --filter @skriptoteket/spa build` after `PR-0085` draft-kind lifecycle changes (PASSED).
- 2026-03-21: `pdm run pytest -m 'integration and docker' tests/integration/database/test_classroom_planner_migration.py -q` after `PR-0085` migration changes (PASSED).
- 2026-03-21: `pdm run ruff check src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py src/skriptoteket/protocols/classroom_planner.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/web/apps/classroom_planner/test_api.py tests/integration/database/test_classroom_planner_migration.py migrations/versions/6b44e9b5d3c1_classroom_planner_draft_kind_and_.py scripts/classroom_planner_draft_kind_api_smoke.py` after `PR-0085` draft-kind lifecycle changes (PASSED).
- 2026-03-21: `pdm run db-upgrade` against the local dev DB after adding `6b44e9b5d3c1_classroom_planner_draft_kind_and_.py` (PASSED).
- 2026-03-21: `pdm run python -m scripts.classroom_planner_draft_kind_api_smoke --base-url http://127.0.0.1:5173` after `PR-0085` draft-kind lifecycle changes (PASSED). Verified:
  - seating drafts can stay active across different classes for the same owner
  - grouping and seating drafts can coexist for the same class without superseding each other
  - re-resolving the same class and kind returns the existing active draft
  - summary saved under `.artifacts/pr-0085-live-check/draft-kind-summary.json`
- 2026-03-21: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` after `PR-0085` draft-kind lifecycle changes (PASSED). Verified:
  - the current launcher still opens the planner cleanly after the new `draft_kind` contract
  - the reusable Klassrumskartan smoke still reaches the live workspace
  - screenshot saved under `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
- 2026-03-21: `pdm run python -u - <<'PY' ...` local Playwright/request smoke against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` using `scripts._playwright_config.get_config()`, `scripts.playwright_ui_smoke._launch_chromium`, and the bootstrap superuser via the protected-route login modal (PASSED). Verified:
  - default active planner shell no longer exposes `Placeringprofil`
  - grouping view shows the new task hint and does not leak assigned seat IDs
  - clicking a student in grouping does not open the seating notes drawer
  - seating view does not leak the group badge/id text
  - clicking a student in seating opens `Elevanteckningar`
  - screenshot saved under `.artifacts/pr-0082-live-check/planner-cleaned-surface.png`
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
  - planner entry smoke PASSED at that earlier checkpoint: selected seeded class + room, opened planner, and confirmed the default workspace no longer showed `Elevmetadata i regelmotor` or `Historikregler`.
  - class/classroom modal smoke PASSED: opened `Redigera klasslista` and `Redigera klassrum`, verified `Spara klassrum` is reachable, and confirmed outside-corner clicks close both dialogs after the dedicated backdrop fix.
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

- Broader repo-wide lint/typecheck/test suites have still not been rerun after the ST-24-01 implementation slice.
- The ad hoc live smokes created several dev-only roster/template rows in the local database; they are harmless but noisy.
- `PlannerWorkspaceShell.vue` still hosts both task shells in one component even though draft-kind gating now hides the opposite surface; deeper route/state separation still belongs to `ST-24-02`.
- The planner currently has no visible randomize button because the old global `Slumpa` contract has been pruned, while the future split randomizers belong to `ST-24-03` and `ST-24-04`.

## Next Steps

- Start `PR-0090` for `ST-24-03`: add the grouping draft-history backend/domain/API contract that supports bounded undo/redo inside one active draft.
- Keep grouping and seating on the same simplified model: autosaved active draft, bounded recent history for undo/redo, and later explicit export for durable file-vault artifacts.
- Keep export out of `ST-24-03`; finish grouping fundamentals and draft continuity first.
