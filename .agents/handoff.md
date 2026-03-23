# Session Handoff
Keep this file updated so the next session can pick up work quickly.

## Editing Rules (do not break structure)

- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files instead.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `.agents/readme-first.md` + `docs/`.

## Snapshot

- Date: 2026-03-23
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `ST-24-01`, `ST-24-05`, `ST-24-02`, `PR-0090`, `PR-0091`, `PR-0092`, `PR-0094`, `PR-0095`, `PR-0096`, `PR-0097`, `PR-0098`, `PR-0099`, and `PR-0100`.

## Status

- PR-0090 is DONE. Implemented bounded undo/redo history (10 steps) inside the active grouping draft.
- PR-0091 is DONE. Grouping now has its own `Slumpa`, an explicit blank `Nytt grupputkast`, and larger group cards render without clipping.
- PR-0091 follow-up fixes are DONE. Group-card up/down controls now update meaningful persisted ordering, and the shared grouping API serializer no longer depends on a private helper leak.
- Backend lifecycle: added `CreateGroupingDraftHandler` plus `POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/new` so blank grouping drafts supersede the previous active grouping draft cleanly instead of overloading `resolve`.
- Frontend store: `useClassroomState.ts` now exposes `startNewGroupingDraft()` and `randomizeGroups()`, with pure grouping-randomize logic kept in `classroomPlannerStoreMutations.ts`.
- Frontend UI: grouping controls live in `GroupBoard.vue`; `PlannerWorkspaceShell.vue` forwards explicit new-draft requests; `GroupCard.vue` now wraps student cards cleanly for larger groups.
- Group ordering: `moveGroup()` now preserves user-visible reorder intent instead of re-sorting by stale `sort_order`, so group-card up/down controls are safe to reuse during later PDF/XLSX export work.
- Group naming: default names are now positional labels backed by `name_is_custom`. Untouched defaults renumber automatically on reorder/delete, while teacher-entered custom names stay fixed.
- Live smoke: `scripts/playwright_classroom_planner_smoke.py` now verifies grouping rename + `Slumpa` + blank `Nytt grupputkast` before continuing through seating, overview return, and landing exit/discard.
- Live smoke also verifies grouping reorder in the browser: custom names stay fixed, default names remain positional, and `Ordning` badges stay meaningful after reordering.
- PR-0092 is now tightened at the planning level:
  - undo/redo stays grouping-only
  - pending autosave now flushes before undo/redo
  - the existing compact autosave badge stays; no broad top-panel redesign
  - `Nytt grupputkast` remains a draft-lifecycle boundary outside undo/redo
- PR-0092 is DONE locally. `GroupBoard.vue` exposes grouping-only `Ångra` / `Gör om`, `useClassroomState.ts` owns flush-first undo/redo orchestration, and backend `history_status` is retained as first-class frontend state instead of being dropped on workspace hydration.
- Redo root-cause fix: removed the local redo workaround, made backend `history_status` the authoritative redo source again, and hardened the browser path around focused rename input -> blur/autosave -> undo/redo rehydration.
- Undo becomes available immediately for pending local grouping edits, but only because the store flushes that pending autosave before calling backend undo; no parallel client redo stack remains.
- No-op group renames no longer mark the workspace dirty, which removes blur-driven interference with history controls.
- Browser proof is now green for the exact teacher path: rename first group -> `Ångra` -> `Gör om` -> custom name restored.
- Landing resumable CTA is now aligned with the intended non-destructive behavior:
  - `Fortsätt` resumes the active draft
  - `Stäng` dismisses the CTA reminder locally without deleting or resetting the draft
- The full Playwright baseline is green again with the landing continue/dismiss behavior.
- Seating builder follow-up is now split and implemented locally across `PR-0102` and `PR-0103`, keeping object visuals separate from viewport/ergonomics work.
- PR-0093 planning/docs are now tightened around a desktop-first continuity model: grouping history should stay secondary in a right-side overlay drawer on full-sized viewports, while tablet/phone layouts are ports of that workflow rather than the source of the canonical design.
- PR-0093 now explicitly includes a small historic-draft management addition: older grouping drafts may be deleted from the continuity drawer with a secondary trash-can action plus confirmation, while the active draft remains free of delete controls in the main workspace.
- PR-0093 is now implemented locally:
  - backend: explicit grouping-history activate/delete handlers plus grouping-only API routes
  - frontend: `PlannerHistoryDrawer.vue` now separates `Aktuellt grupputkast` from `Tidigare grupputkast`, can reopen older grouping drafts, and can delete historic grouping drafts with confirmation
  - store/view: `useClassroomState.ts` and `ClassroomPlannerView.vue` now orchestrate historic draft activation/deletion without adding any delete control to the active workspace
- Live browser continuity proof is green locally: create another grouping draft, reopen an older grouping draft from the overlay drawer, delete a historic grouping draft with confirmation, and confirm the active draft still reopens with the renamed group intact.
- Planner shell follow-up is now implemented locally:
  - `Översikt` is quiet and no longer duplicates `Grupper` / `Sittplatser` entry actions
  - the segmented toggle is now the only mode switch
  - grouping history now opens from the grouping action row in `GroupBoard.vue`
  - seating now has its own minimal toolbar row with `Redigera klassrum`
- Seating terminology and room-builder model are also updated locally:
  - visible copy now prefers `Sittplatser`, `Sittschema`, and `Klassrum`
  - `Whiteboard`, `Fönster`, and `Dörr` are now wall-bound objects in the room builder
  - `Kateder`, `Runt bord`, `Fyrkantigt bord`, and `Bänk` are floor objects
  - tables and benches are visual room objects only; seats remain separate placements
- `PR-0101`, `PR-0102`, and `PR-0103` are DONE locally:
  - saved room templates carry `grid_cols` / `grid_rows`, the room builder supports stepwise width/height resize plus ghost placement, and wall anchoring stays pointer-driven
  - object rendering now uses shared fixture artwork, true round tables, centered `Whiteboard` / `Kateder` labels, bench coalescing, and dedicated wall-band rendering so wall objects never consume floor tiles
  - the room-builder modal now uses a larger desktop footprint with a narrower tools column, explicit zoom (`-`, `+`, `Anpassa`), `Rensa`, and circular seats across builder, preview, and live seating
- Competitive-games planning docs are corrected back to the intended meaning of "programme": a cross-cutting delivery/programme reference for epics, stories, and shared infrastructure work, tracked in `docs/reference/ref-competitive-games-cross-cutting-programme.md`.
- Competitive-games planning is now formally open for implementation: `REV-EPIC-25` is approved, `ADR-0073` is accepted, and `EPIC-25` is active.
- `ST-25-01` is DONE locally across `PR-0094`, `PR-0095`, and `PR-0096`: Flunk-Out Frenzy is registered/discoverable as a bespoke curated app, resolves through `AppHostView.vue`, and exposes the minimal typed bootstrap via `src/skriptoteket/web/api/v1/apps_flunk_out_frenzy.py`.
- `ST-25-02` is DONE locally across `PR-0097` through `PR-0100`: the route now delivers the immersive shell, runtime boundary, prototype-alpha physics/rules, and Pixi/Howler integration with a verified local 3-ball loop.
- `ST-25-02` planning decisions are now locked for decomposition:
  - commit directly to PixiJS + Rapier 2D + Howler
  - author the first table as typed TypeScript modules first, then extract later if needed
  - remove replay work from the immediate slice entirely
  - keep shell UI to HUD + Start/Pause/Restart/Mute
  - defer drop targets, scoop behavior, ramps, backend score submission, and leaderboard UI
- Competitive-games planning docs are now renamed around `games.flunk_out_frenzy` / `Flunk-Out Frenzy` instead of the earlier Pinball Teacher placeholder.
- `PR-0097` is DONE locally and corrected twice: the route now uses immersive top-bar-only chrome plus a single staged machine composition instead of the earlier generic/dashboard shell, while `GameHost.vue` owns a playfield-framed runtime placeholder seam for `PR-0098` and settings/bootstrap metadata stay hidden behind a drawer.
- `PR-0098` and `PR-0099` are DONE locally: the prototype-alpha slice now has Rapier-backed physics, a pure rules engine, corrected mirrored flippers, viewport-safe board sizing, and a verified 3-ball loop with drain -> respawn -> game over plus score/multiplier progression.
- `PR-0100` is DONE locally: `GameRuntime` now owns Pixi rendering and Howler audio adapters, `GameHost.vue` is a true runtime surface instead of a DOM simulation layer, and live route proof confirms Start/Pause/Restart/Mute plus clean route-leave disposal.

## Previous Sessions

## Verification

- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py -q`; `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q`; `pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_history_unit.py -q` (ALL PASSED).
- 2026-03-22: `pdm run alembic upgrade head` (PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py` (PASSED).
- 2026-03-22: `PYTHONPATH=src pdm run python -c 'from skriptoteket.di.curated_apps import CuratedAppsProvider; print("di-import-ok")'` (PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py tests/unit/web/apps/classroom_planner/test_api.py -q` (31 PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py` (PASSED).
- 2026-03-22: `pdm run pytest -m 'integration and docker' tests/integration/database/test_classroom_planner_migration.py -q` (PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (29 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (27 PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/planner_context.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py src/skriptoteket/web/router.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/planner_context.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/classroomPlannerTypes.ts src/views/apps/useClassroomState.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/GroupBoard.vue src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.vue src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run ruff check scripts/playwright_classroom_planner_smoke.py` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/GroupCard.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/useClassroomState.spec.ts` (30 PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (29 PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/web/api/v1/apps_classroom_planner_draft_contracts.py src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/web/api/v1/apps_classroom_planner_draft_contracts.py src/skriptoteket/web/api/v1/apps_classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.vue src/views/apps/components/GroupCard.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run docs-validate` (PASSED).
- 2026-03-22: `pdm run docs-validate` (PASSED after adding `ST-25-02` PR planning docs `PR-0097` through `PR-0100`).
- 2026-03-22: `pdm run docs-validate` (PASSED after renaming the competitive-games planning docs from the Pinball Teacher placeholder to Flunk-Out Frenzy and removing stale replay-seam wording from `ST-25-02`).
- 2026-03-22: `pdm run docs-validate` (PASSED after correcting the competitive-games "programme" scope back to a cross-cutting delivery reference and removing the mistaken hub story).
- 2026-03-22: `pdm run docs-validate` (PASSED after promoting `EPIC-25` to `active` and confirming the review/ADR/epic status chain is valid).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after adding reorder assertions; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pdm run db-upgrade` (PASSED; required locally after adding the `name_is_custom` draft-group migration).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (34 PASSED).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py -q` (33 PASSED).
- 2026-03-22: `pdm run pytest -m 'integration and docker' tests/integration/database/test_classroom_planner_migration.py -q` (PASSED).
- 2026-03-22: `pdm run ruff check migrations/versions/71e8b6f24c1a_add_group_name_custom_flag.py src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py scripts/playwright_classroom_planner_smoke.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/web/api/v1/apps_classroom_planner.py` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/classroomPlannerTypes.ts src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.vue src/views/apps/components/GroupCard.spec.ts src/views/apps/components/RoomCanvas.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after adding default/custom naming assertions; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (29 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (40 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/classroomPlannerTypes.ts src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/components/GroupBoard.vue src/views/apps/components/GroupBoard.spec.ts src/views/apps/useClassroomState.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run ruff check scripts/playwright_classroom_planner_smoke.py` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after adding grouping browser-level undo verification; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (29 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (42 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/classroomPlannerStoreMutations.ts src/views/apps/components/GroupBoard.vue src/views/apps/components/GroupCard.vue src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pdm run python - <<'PY' ... rename -> Ångra -> Gör om focused browser proof ... PY` (PASSED; browser proof for redo path only).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (FAILED at landing cleanup: could not find landing-page `Avsluta utkast` after workspace `Avsluta`; redo path itself returned `200/200` in backend logs and passed in focused browser proof).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerSelectionGate.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/components/PlannerSelectionGate.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerSelectionGate.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pdm run docs-validate` (PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after switching the landing resumable CTA to continue + dismiss and hardening the smoke selectors around the CTA container).
- 2026-03-22: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (35 PASSED after adding grouping-history activate/delete handlers and API routes).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerHistoryDrawer.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts` (7 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/ClassroomPlannerView.spec.ts` (PASSED as part of the focused PR-0093 view pass).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts -t "activates a historical grouping draft through the dedicated lifecycle endpoint|deletes a historical grouping draft through the dedicated lifecycle endpoint" --reporter=verbose` (2 PASSED; targeted store verification for new history actions).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/ClassroomPlannerView.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerHistoryDrawer.vue src/views/apps/components/PlannerHistoryDrawer.spec.ts src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/components/PlannerClassWorkspace.spec.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_history.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/grouping_history.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_grouping.py` (PASSED).
- 2026-03-22: `pdm run ruff check scripts/playwright_classroom_planner_smoke.py` (PASSED after extending the smoke to cover grouping continuity + historic delete).
- 2026-03-22: local runtime corrected back to `.env` / Docker Postgres on `localhost:55432`; the accidental native `localhost:5432/skriptoteket` database was removed after confirming it only held throwaway smoke data.
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (27 PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/components/CreateRoomTemplateModal.vue src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/RoomCanvas.vue src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/ClassroomPlannerView.vue src/views/apps/roomFixtureLayout.ts src/views/apps/classroomPlannerTypes.ts` (PASSED).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-22: `pdm run ruff check src/skriptoteket/domain/curated_apps/classroom_planner/models.py scripts/playwright_classroom_planner_smoke.py` (PASSED).
- 2026-03-22: `pdm run mypy src/skriptoteket/domain/curated_apps/classroom_planner/models.py` (PASSED).
- 2026-03-22: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q` (20 PASSED).
- 2026-03-22: `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED after moving the grouping-history trigger into the grouping toolbar and scoping the seating smoke to the seating surface; artifact in `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`).
- 2026-03-22: `pdm run python - <<'PY' ... classroom builder proof ... PY` (PASSED; verified seat + door can share an edge cell, whiteboard rejects center placement, and `Runt bord` / `Fyrkantigt bord` / `Bänk` can be added live; artifact in `.artifacts/classroom-builder-proof/classroom-builder-proof.png`).
- 2026-03-22: `pdm run docs-validate` (PASSED after tightening `ST-24-04` and adding `PR-0101` / `PR-0102`).
- 2026-03-23: `pdm run db-upgrade`; `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/roomFixtureLayout.spec.ts src/views/apps/roomFixturePresentation.spec.ts src/views/apps/components/RoomFixtureArtwork.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/RoomCanvas.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/roomFixturePresentation.ts src/views/apps/roomFixturePresentation.spec.ts src/views/apps/components/RoomFixtureArtwork.vue src/views/apps/components/RoomFixtureArtwork.spec.ts src/views/apps/components/CreateRoomTemplateModal.vue src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/RoomCanvas.vue src/views/apps/components/RoomCanvas.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa build`; `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/apps/classroom_planner/test_services.py tests/unit/application/apps/classroom_planner/test_asset_delete_guards.py -q`; live browser check against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` with extra local SPA servers shut down (PASSED for `PR-0101` plus current `PR-0102` fixture-rendering work; screenshot copied to `.artifacts/classroom-builder-proof/pr0102-room-builder-5173.png`).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/roomBuilderViewport.spec.ts src/views/apps/roomFixturePresentation.spec.ts src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/RoomCanvas.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/roomBuilderViewport.ts src/views/apps/roomBuilderViewport.spec.ts src/views/apps/roomSeatPresentation.ts src/views/apps/components/RoomSeatToken.vue src/views/apps/components/SeatNode.vue src/views/apps/components/CreateRoomTemplateModal.vue src/views/apps/components/CreateRoomTemplateModal.spec.ts src/views/apps/components/RoomCanvas.vue src/views/apps/components/RoomCanvas.spec.ts src/views/apps/roomFixturePresentation.ts src/views/apps/roomFixturePresentation.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa build`; `pdm run ruff check scripts/playwright_classroom_planner_smoke.py`; `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173` (PASSED on the canonical local app route with only `:5173` + backend `:8000` active; artifacts in `.artifacts/classroom-planner-smoke/`).
- 2026-03-22: `pdm run pytest tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_apps_api_routes.py tests/unit/web/test_catalog_curated_app_discoverability.py -q`; `pdm run ruff check src/skriptoteket/infrastructure/curated_apps/registry.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_apps_api_routes.py tests/unit/web/test_catalog_curated_app_discoverability.py`; `pdm run mypy src/skriptoteket/infrastructure/curated_apps/registry.py tests/unit/infrastructure/curated_apps/test_registry.py tests/unit/web/test_apps_api_routes.py tests/unit/web/test_catalog_curated_app_discoverability.py` (ALL PASSED for `PR-0094`).
- 2026-03-22: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/AppHostView.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/AppHostView.vue src/views/apps/FlunkOutFrenzyView.vue src/views/AppHostView.spec.ts src/views/apps/FlunkOutFrenzyView.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa build` (ALL PASSED for `PR-0095`).
- 2026-03-22: `pdm run python - <<'PY' ... Flunk-Out Frenzy protected-route browser proof ... PY` (PASSED; logged in via `/login`, opened `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`, verified the bespoke shell heading + `Spelyta` + runtime host placeholder, and wrote `.artifacts/flunk-out-frenzy-route-check/flunk-out-frenzy-route.png`).
- 2026-03-23: `pdm run pytest tests/unit/application/apps/flunk_out_frenzy/test_bootstrap.py tests/unit/web/apps/flunk_out_frenzy/test_api.py -q`; `pdm run ruff check src/skriptoteket/application/curated_apps/flunk_out_frenzy src/skriptoteket/protocols/flunk_out_frenzy.py src/skriptoteket/web/api/v1/apps_flunk_out_frenzy.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/router.py tests/unit/application/apps/flunk_out_frenzy/test_bootstrap.py tests/unit/web/apps/flunk_out_frenzy/test_api.py`; `pdm run mypy src/skriptoteket/application/curated_apps/flunk_out_frenzy src/skriptoteket/protocols/flunk_out_frenzy.py src/skriptoteket/web/api/v1/apps_flunk_out_frenzy.py` (ALL PASSED for `PR-0096` backend).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/FlunkOutFrenzyView.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts src/views/apps/useFlunkOutFrenzyBootstrap.ts src/views/apps/flunkOutFrenzyTypes.ts` (PASSED for `PR-0096` frontend).
- 2026-03-23: `pdm run python - <<'PY' ... Flunk-Out Frenzy bootstrap browser proof ... PY` (PASSED; logged in via `/login`, opened `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`, verified the bootstrap-backed ready state including `flunk_out_frenzy.prototype_alpha.v1`, feature flags, and the runtime host placeholder, and wrote `.artifacts/flunk-out-frenzy-bootstrap-check/flunk-out-frenzy-bootstrap.png`).
- 2026-03-23: `pdm run docs-validate`; `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/FlunkOutFrenzyView.spec.ts src/components/apps/flunk-out-frenzy/GameHost.spec.ts src/components/layout/AuthLayout.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts src/components/apps/flunk-out-frenzy/GameHost.vue src/components/apps/flunk-out-frenzy/GameHost.spec.ts src/components/apps/flunk-out-frenzy/gameHostTypes.ts src/components/layout/AuthLayout.vue src/components/layout/AuthLayout.spec.ts src/components/layout/AuthTopBar.vue`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa build` (docs/tests/lint/build PASSED for the PR-0097 redesign).
- 2026-03-23: `pdm run python - <<'PY' ... Flunk-Out Frenzy immersive/composition browser proof ... PY` (PASSED after the redesign on both the built/backend route and a clean restarted Vite dev server; `http://127.0.0.1:8000/apps/games.flunk_out_frenzy` wrote `.artifacts/flunk-out-frenzy-composition-check/flunk-out-frenzy-composition-backend.png`, and `http://127.0.0.1:5173/apps/games.flunk_out_frenzy` wrote `.artifacts/flunk-out-frenzy-composition-check/flunk-out-frenzy-composition-dev.png`).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run $(rg --files frontend/apps/skriptoteket/src/components/apps/flunk-out-frenzy -g '*.spec.ts' | sed 's#^frontend/apps/skriptoteket/##') frontend/apps/skriptoteket/src/views/apps/FlunkOutFrenzyView.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/components/apps/flunk-out-frenzy/game src/components/apps/flunk-out-frenzy/GameHost.vue src/components/apps/flunk-out-frenzy/GameHost.spec.ts src/views/apps/FlunkOutFrenzyView.vue src/views/apps/FlunkOutFrenzyView.spec.ts`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa build`; `pdm run docs-validate` (PASSED for `PR-0100` close-out).
- 2026-03-23: `pdm run python - <<'PY' ... Flunk-Out Frenzy PR-0100 live route proof ... PY` (PASSED against `http://127.0.0.1:5173/apps/games.flunk_out_frenzy`; verified Start/Pause/Fortsätt/Starta om/Ljud, confirmed zero gameplay API calls after a short post-load settle, and confirmed route leave removes the runtime canvas; artifact in `.artifacts/pr-0100-playable-proof/flunk-out-frenzy-pr0100-dev.png`).

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
```

## Known Issues / Risks

- Integration tests for repository history were moved to unit tests due to environmental loop mismatch issues in the test runner; the repository logic itself is thoroughly covered by `test_classroom_planner_history_unit.py`.
- Seating drafts do not yet push to history (intentional scope constraint for PR-0090); they will inherit the same model in ST-24-04.

## Next Steps

- Review the local seating-builder worktree and commit when ready; the next seating slice beyond `PR-0103` is not planned yet.
- Competitive-games lane: `ST-25-01` and `ST-25-02` are done locally; next step is `PR-0104` remediation, then `ST-25-03` pending-score submission and typed leaderboard planning/implementation.
