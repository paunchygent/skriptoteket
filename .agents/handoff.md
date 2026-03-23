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
- Completed: `ST-24-01`, `ST-24-05`, `ST-24-02`, `ST-24-03`, `ST-24-04`, `PR-0090`, `PR-0091`, `PR-0092`, `PR-0093`, `PR-0101`, `PR-0102`, `PR-0103`, `PR-0104`, `PR-0105`, and `PR-0106`.

## Status

- Klassrumskartan fundamentals lane is largely shipped:
  - grouping has blank `Nytt grupputkast`, grouping-only undo/redo, and a continuity drawer with reopen/delete for historic grouping drafts
  - overview is now quiet; the segmented toggle is the single mode switch
  - seating builder slices `PR-0101` to `PR-0103` are done (resize, ghost preview, wall-vs-floor rendering, artwork, zoom, `Anpassa`, `Rensa`, circular seats)
- `PR-0105` is now implemented locally:
  - backend: explicit seating lifecycle routes in `src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py`
  - application: `src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_drafts.py` and `seating_history.py`
  - frontend: `PlannerWorkspaceShell.vue` exposes `Historik`, `Nytt sittschema`, and `Redigera klassrum` in the seating action row
  - continuity: seating reuses `PlannerHistoryDrawer.vue` for `Aktuellt sittschema` + `Tidigare sittscheman`
  - guardrail: `Nytt sittschema` requires a selected classroom and otherwise focuses the classroom picker with a teacher-facing hint
  - safety: seating create/open/delete actions now lock the seating toolbar and drawer while in flight
- Ruthless review of `PR-0105` was completed with a `GPT-5.4` high subagent:
  - busy-state / reentrancy issue: fixed and covered by tests
  - non-null `template_id` contract gap: fixed and covered by tests
  - flaky shared smoke dependency: replaced with a dedicated `PR-0105` browser proof
- `PR-0106` is now implemented locally:
  - backend/domain: draft history is now neutral across grouping and seating via `DraftHistoryStatus`
  - repository: seating snapshots persist `seat_assignments`, remain bounded to 10 steps, ignore
    `template_id` on replay, and reset history when the classroom changes so template switching is
    not undoable
  - application/web: shared `/drafts/{draft_id}/undo` and `/redo` handlers now allow seating drafts
    without pretending the contract is grouping-only
  - frontend: `PlannerWorkspaceShell.vue` now exposes seating `Ångra` / `Gör om`, and
    `useClassroomState.ts` flushes autosave before both grouping and seating history actions
  - proof: the dedicated browser script now verifies seating undo/redo, continuity staying
    draft-level, and classroom switching staying outside seating undo/redo
- `ST-24-04` is now closed, but `EPIC-24` remains active:
  - `ST-24-06` is now in progress as the remaining seating `Slumpa` fundamentals slice
  - `ST-24-07` is now in progress as the compact overview-first management slice via `PR-0110`
  - `ST-24-08` is now drafted as the final landing cutover and exit-to-origin slice
  - `PR-0109` is shipped, `PR-0110` is the active implementation slice, and `PR-0111` plus `PR-0112` are the next overview follow-ups before the later cutover story
- `REV-EPIC-24` amendment is now approved and recorded in `docs/backlog/reviews/review-epic-24-group-seating-studio-slice-2-planning.md`.
- `PR-0109` is now implemented locally:
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerStoreMutations.ts` adds seating full-draft randomization
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts` exposes seating `Slumpa` through the current autosave/history path
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue` adds the classroom-gated seating `Slumpa` action
  - deterministic unit coverage proves the full-reshuffle contract rather than only filling empty seats
  - the dedicated seating browser proof now covers `Slumpa` wiring plus autosave and undo/redo compatibility
- `PR-0110` is now implemented locally:
  - `PlannerClassWorkspace.vue` expands `Översikt` into a compact desktop-first class/classroom dashboard
  - overview now exposes class switching, class creation/editing, classroom selection, compact preview, and explicit classroom create/edit/delete actions
  - `ClassroomPlannerView.vue` now keeps an overview-local selected classroom state synced to the active seating draft when appropriate
  - grouping remains classroom-agnostic on entry, while seating carries the overview-selected classroom forward
  - the current polish pass also aligns counters to the title baseline, moves the selected classroom into the top panel context, and tightens overview spacing after the initial design review
  - focused view/component tests cover roster switching from overview and opening classroom editing from the selected overview classroom
- Competitive-games lane is separate:
  - `ST-25-01` and `ST-25-02` are done through `PR-0104`
  - next planned chain there is `PR-0107` -> `PR-0108` -> `ST-25-03`

## Previous Sessions

- Older detailed verification history is now carried by story/epic docs plus git history; keep this handoff focused on the current sprint-critical state only.

## Verification

- 2026-03-23: `lsof -nP -iTCP:5173 -sTCP:LISTEN`; `lsof -nP -iTCP:4173 -sTCP:LISTEN`; `lsof -nP -iTCP:8000 -sTCP:LISTEN` (confirmed canonical local app on `127.0.0.1:5173`, backend on `127.0.0.1:8000`, and no extra `:4173` server).
- 2026-03-23: `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (42 PASSED).
- 2026-03-23: `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q` (24 PASSED after adding the non-null `template_id` boundary test).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts -t 'starts a brand-new seating draft through the dedicated lifecycle endpoint|activates a historical seating draft through the dedicated lifecycle endpoint|deletes a historical seating draft through the dedicated lifecycle endpoint' --reporter=verbose` (3 PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (29 PASSED after adding seating busy-state/reentrancy coverage).
- 2026-03-23: `pdm run ruff check src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_history.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py src/skriptoteket/web/router.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py scripts/playwright_classroom_planner_smoke.py scripts/playwright_pr_0105_seating_continuity.py` (PASSED).
- 2026-03-23: `pdm run mypy src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_drafts.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/seating_history.py src/skriptoteket/application/curated_apps/classroom_planner/__init__.py src/skriptoteket/di/curated_apps.py src/skriptoteket/web/api/v1/apps_classroom_planner_seating.py` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/ClassroomPlannerView.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerHistoryDrawer.vue`; `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit`; `pnpm -C frontend --filter @skriptoteket/spa build` (PASSED).
- 2026-03-23: `pdm run python -m scripts.playwright_pr_0105_seating_continuity --base-url http://127.0.0.1:5173` (PASSED; proved classroom-required `Nytt sittschema`, verified a fresh seating draft clears a real seat assignment, reopened historic seating to restore that assignment, then deleted the remaining historic draft; artifact in `.artifacts/classroom-planner-smoke/pr0105-seating-continuity-proof.png`).
- 2026-03-23: `pdm run docs-validate` (PASSED after closing out `PR-0105`, updating `ST-24-04`, `EPIC-24`, and this handoff).
- 2026-03-23: `pdm run docs-validate` (PASSED after drafting `EPIC-24`, `ST-24-06`, `ST-24-07`, `ST-24-08`, and `PR-0109` to `PR-0111`).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts` (PASSED; 46 tests, including deterministic seating `Slumpa` reshuffle coverage and seating-toolbar action coverage).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-23: `pdm run ruff check scripts/playwright_pr_0105_seating_continuity.py` (PASSED).
- 2026-03-23: `pdm run python -m scripts.playwright_pr_0105_seating_continuity --base-url http://127.0.0.1:5173` (PASSED; now also proves seating `Slumpa` wiring with autosave and undo/redo on the live app; artifact in `.artifacts/classroom-planner-smoke/pr0105-seating-continuity-proof.png`).
- 2026-03-23: `pdm run docs-validate` (PASSED after `REV-EPIC-24` amendment approval, `ST-24-06` / `PR-0109` move to `in_progress`, and the `PR-0109` implementation notes).
- 2026-03-23: `pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q` (49 PASSED; includes repository coverage for seating history reset on classroom switch and non-replay of `template_id`).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts --reporter=verbose` (43 PASSED; covers seating undo/redo store orchestration, seating action-row controls, and lifecycle busy-state locking).
- 2026-03-23: `pdm run ruff check src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/protocols/classroom_planner.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/web/api/v1/apps_classroom_planner.py tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py scripts/playwright_classroom_planner_smoke.py scripts/playwright_pr_0105_seating_continuity.py` (PASSED).
- 2026-03-23: `pdm run mypy src/skriptoteket/domain/curated_apps/classroom_planner/models.py src/skriptoteket/protocols/classroom_planner.py src/skriptoteket/infrastructure/repositories/classroom_planner.py src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py src/skriptoteket/web/api/v1/apps_classroom_planner.py` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/useClassroomState.ts src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.vue src/views/apps/components/PlannerWorkspaceShell.spec.ts` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-23: `pdm run python -m scripts.playwright_pr_0105_seating_continuity --base-url http://127.0.0.1:5173` (PASSED; proved seating `Ångra` / `Gör om`, confirmed undo/redo stays inside the active draft while the continuity drawer remains empty until a second seating draft exists, verified historic reopen/delete still works, and verified switching classroom resets seating history instead of making classroom changes undoable; artifact in `.artifacts/classroom-planner-smoke/pr0105-seating-continuity-proof.png`).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (PASSED; 22 tests covering compact overview controls, overview class switching, overview class creation, overview classroom edit flow, and classroom-aware seating entry while grouping stays classroom-agnostic).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/ClassroomPlannerView.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/components/PlannerClassWorkspace.spec.ts` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-23: `BASE_URL=http://127.0.0.1:5173 pdm run python - <<'PY' ... PY` authenticated local Playwright probe against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` (PASSED; created a real roster and classroom, opened `Klassöversikt`, verified `Byt klass`, `Välj klassrum`, and compact classroom preview rendering; nearby debug screenshot artifact in `.artifacts/classroom-planner-smoke/pr0110-overview-debug.png`).
- 2026-03-23: `pdm run docs-validate` (PASSED after moving `ST-24-07` / `PR-0110` to `in_progress` and updating handoff for the local `PR-0110` implementation state).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (PASSED; 25 tests after overview spacing, counter typography/baseline alignment, and top-panel classroom-context polish).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec eslint src/views/apps/components/PlannerClassWorkspace.vue src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerView.vue src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/components/PlannerConfirmationDialog.vue` (PASSED).
- 2026-03-23: `pnpm -C frontend --filter @skriptoteket/spa exec vue-tsc --noEmit` (PASSED).
- 2026-03-23: `BASE_URL=http://127.0.0.1:5173 pdm run python - <<'PY' ... PY` authenticated local Playwright probe against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` (PASSED; opened `Testklass A`, verified the current `Klassöversikt` surface plus `Välj klassrum`, and saved `.artifacts/pr0110-live-check/overview-dashboard-current.png`).
- 2026-03-23: `pdm run docs-validate` (PASSED after drafting `PR-0112` and recording the latest `PR-0110` overview-polish verification in handoff).
- 2026-03-23: `pdm run docs-validate` (PASSED after drafting `PR-0112` for overview design simplification and seamless workspace transitions, updating `ST-24-07` decomposition, and indexing the new PR doc).

## How to Run

```bash
# Setup
docker compose up -d db && pdm run db-upgrade

# Development (backend + SPA)
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local

# Focused verification
pdm run pytest tests/unit/infrastructure/repositories/test_classroom_planner_review_fixes.py tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py -q
pnpm -C frontend --filter @skriptoteket/spa exec vitest run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
pdm run python -m scripts.playwright_pr_0105_seating_continuity --base-url http://127.0.0.1:5173
pdm run docs-validate
```

## Known Issues / Risks

- Room-template editing must stay outside seating undo/redo; only seating-draft state belongs to the seating history stack.
- `scripts/playwright_classroom_planner_smoke.py` still covers a broader surface than PR-level proofs; prefer the dedicated `PR-0105` browser proof for seating lifecycle regressions.
- `ST-24-07` intentionally duplicates the resumable CTA in both landing and overview before the
  later big-bang cutover in `ST-24-08`; no compatibility layer should survive the final cutover.
- Seating `Slumpa` keeps its exact full-reshuffle contract anchored in deterministic unit tests;
  the live Playwright proof is intentionally smoke-level for the random UI path.

## Next Steps

- EPIC-24 next planned implementation chain is:
  - present `PR-0110` for approval, then commit/push it
  - then land `PR-0111` (duplicated resumable CTA + overview-entry/browser proof)
  - then land `PR-0112` (overview design simplification + seamless workspace transitions)
  - `ST-24-08` only after overview-first management is fully proven
- Competitive-games lane remains separate and should not be conflated with Klassrumskartan planning.
