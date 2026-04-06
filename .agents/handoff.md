# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines; move history to `docs/`.
## Snapshot
- Date: 2026-04-06
- Branch: `main` + local changes
- Current sprint: Sprint 24
- Production: Full Vue SPA
- Completed: `PR-0223` checkpoint 3 docs closed earlier; `PR-0226` now implemented locally with review cleared
## Status
- `PR-0226` is implemented locally across the shared planner shell and grouping layout contract. Shared wrapper/layout logic now lives in `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceModeSurface.vue` and `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`, with both `PlannerWorkspaceShell.vue` and `ClassroomPlannerGuestWorkspaceShell.vue` consuming the same sticky toolbar + pane-shell contract.
- `PR-0227` is now done locally as the next bounded `ST-29-11` follow-up: `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`, `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`, and the focused component specs now freeze a desktop-only card-floor contract where the empty/default 4-group 2x2 board measures exactly `480px` at `1440x900`, while the underlying `234px` card rule persists as a desktop `min-height` floor rather than a universal hard cap once students are assigned.
- Grouping layout stabilization is live locally: `PlannerGroupingWorkspacePane.vue`, `PlannerStudentPool.vue`, `GroupBoard.vue`, and `GroupCard.vue` now freeze the documented `480px` desktop lane floor plus `56px` assigned-row / `112px` empty-drop-zone floors. Focused proof was added in `PlannerGroupingWorkspacePane.smart-rules.spec.ts`, `GroupBoard.spec.ts`, and `GroupCard.spec.ts`.
- `PR-0227` browser proof now lives in `scripts/playwright_pr_0227_group_board_height_contract_check.py`. It follows the existing targeted Playwright proof pattern, reuses the shared planner/browser helpers, and writes screenshots to `.artifacts/pr-0227-group-board-height-check/` for both public and authenticated routes.
- The guest regression reported after grouping mutations is fixed in `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftPersistence.ts`. Grouping autosave now preserves `selected_template_local_id` instead of overwriting it with `null`, so overview-selected classrooms survive `Slumpa` / grouping edits and `Sittplatser` stays enabled.
- Fresh grouping drafts are now normalized to 4 default groups in both lanes: guest/browser-owned seeding in `classroomPlannerGuestDraftPersistence.ts` and authenticated/backend seeding in `src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py`.
- Docs are updated locally: `docs/backlog/prs/pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md` is now `done`, `docs/backlog/prs/pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md` now freezes the desktop `min-height` plus empty-state exactness split, the supplemental reviews in `docs/backlog/reviews/review-epic-29-klassrumskartan-desktop-first-workspace-overhaul.md` are now `approved`, and the `ST-29-11` / `EPIC-29` implementation summaries were refreshed.
## Verification
- `pdm run fe-test src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (pass; 8 files / 88 tests)
- `pdm run fe-test src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts` (pass; 10 tests after adding classroom-persistence + 4-group guest seed coverage)
- `pdm run fe-type-check` (pass)
- `pdm run fe-test src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts` (pass; 15 tests for the `PR-0227` board/card contract)
- `pdm run fe-test src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts` (pass; 5 files / 51 tests)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py` (pass; 20 tests, including authenticated grouping-draft seed count)
- `pdm run python -m scripts.playwright_pr_0227_group_board_height_contract_check --base-url http://127.0.0.1:5173` (pass; public + authenticated route proof, screenshots in `.artifacts/pr-0227-group-board-height-check/`, asserts empty 4-card board `480px`, row gap `12px`, card floor `234px`, post-assignment floor persistence, and populated-card growth without internal scrolling)
- `pdm run docs-validate` (pass after `PR-0227` status + implementation verification updates)
- Live browser check, public route `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio`:
  - created roster `SA24D`
  - created classroom `Sal 101`
  - opened fresh `Grupper` draft and confirmed it seeded 4 groups
  - clicked `Slumpa`, waited for `Sparad`, and confirmed the header still showed `Sal 101`
  - confirmed `Sittplatser` stayed enabled and opened successfully after grouping autosave
  - sticky toolbar stayed fully visible in public seating mode while scrolling (`before top=476/bottom=522`, `after top=117/bottom=163` at `1440x900`)
- Live browser check, authenticated route `http://127.0.0.1:5173/apps/classroom.group-seating-studio`:
  - logged in with the bootstrap superuser
  - postponed the guest-upgrade prompt
  - opened a fresh grouping draft and confirmed it now seeded 4 groups instead of 6
  - sticky toolbar stayed fully visible inside the authenticated scroll container (`main.auth-main-content`) while scrolling (`before top=395/bottom=441`, `after top=110/bottom=156`)
## How to Run
```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run fe-test src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerView.spec.ts
pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py
```
## Known Issues / Risks
- The authenticated route still shows the pre-existing guest-upgrade import dialog with `Internal server error`; this did not block the planner verification because `Inte nu` closed it, but the upgrade/import path still needs its own debugging lane.
- `ClassroomPlannerView.spec.ts` still emits the pre-existing suppressed runtime warning from `resolveHomeRosterId(...)` during one centered-shell test even though the suite passes; it was not part of `PR-0226`.
## Next Steps
- If the user wants the lane published now, stage/commit the local `PR-0226` + doc updates and push `main`.
- `PR-0227` close-out is now complete locally; the remaining work is publish/deploy follow-through rather than additional planner implementation for this slice.
- Debug the authenticated guest-upgrade import prompt separately from `PR-0226`; the planner shell/layout work is verified independently of that modal failure.
- Decide whether `ST-29-11` should now be closed as done or whether more dense-control follow-up remains beyond the implemented `PR-0224` / `PR-0225` / `PR-0226` set.
