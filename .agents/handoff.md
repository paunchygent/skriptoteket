# Session Handoff
Keep this file updated so the next session can pick up work quickly.
## Editing Rules (do not break structure)
- Keep the headings and section order exactly as-is; only fill in content.
- Use short bullets; include key file paths (e.g., `src/...`, `docs/...`) and exact commands.
- Do not paste large code blocks; link to files.
- Never include secrets/tokens/passwords or personal data.
- Keep this file under 200 lines.
- When compacting this file, append the removed content directly to `docs/reference/ref-development-changelog.md` first.
## Snapshot
- Date: 2026-04-07
- Branch: `main` + local changes
- Current lane: `PR-0232` guest local continuity, export, and account-only history polish
- Production: Full Vue SPA
- Completed: `PR-0231` is implemented locally with review follow-ups fixed; `PR-0233` is now implemented locally and live-proven against the real `SA24D` / `G20` authenticated guest-upgrade seam; `ST-09-09` is done with the shipped Hemma deploy launcher/monitor path; ShellCheck is now part of pre-commit and `pdm run lint`; active docs guidance now has a canonical development changelog and the stale v0.2 implementation map has been removed
## Status
- `PR-0231` is implemented locally and its retained review follow-ups are fixed. Guest `Regler`, public solver-backed Smart, request streaming limits, persistence rollback, and helper-family throttle wiring are in place.
- `PR-0233` is implemented locally as the narrow `ST-32-05` remediation slice. The authenticated guest-upgrade seam now compares guest templates to real persisted template geometry, deterministically remaps reused-template seat ids through a dedicated helper module, and no longer reproduces the old non-toy template-bearing `500` on `/api/v1/apps/classroom.group-seating-studio/guest-upgrade`.
- `PR-0234` was the blocking `ST-32-06` frontend remediation slice. The assessed root cause was the public guest overview -> grouping seam dropping the selected classroom by opening grouping with `templateId = null`, plus stale pending template refs keeping `Sittplatser` visually enabled after live classroom context was gone.
- Focused failing frontend regressions are now in place locally before any production fix:
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts`
- The `PR-0234` production fix is now implemented locally. A small helper module centralizes the live guest classroom-context rule, overview -> grouping now preserves the selected classroom, and the guest shell now disables `Sittplatser` from the real live context rather than stale pending refs.
- `PR-0235` is now implemented locally. The shared viewport helper keeps the framed-surface fit model across builder / seating / rules, fit-to-view is explicitly capped at `100%`, and the pure helper seam now has focused coverage so the repo no longer relies on stale pre-frame numbers in `useRoomViewportZoom.spec.ts`.
- `PR-0236` is now implemented locally. The stale isolated roster-overview spec now passes `showActions` explicitly when asserting the visible action footer, also proves the hidden-footer case when actions are disabled, and keeps class-list import inside the create/edit workflow.
- `PR-0232` remains the next feature slice after `PR-0234`. It owns guest local undo/redo parity, direct-download export through dedicated public routes, and final account-only history/recovery affordance polish under approved `REV-PR-0231`. The PR doc now explicitly depends on verified `PR-0233` and blocking `PR-0234`, so guest export/checkpoint continuity must keep using the canonical authenticated `/api/v1/apps/.../guest-upgrade` seam rather than introducing a guest-only fallback shape.
- `PR-0232` now also has an explicit required quality gate: the implementation close-out must record one live guest verification pass plus one live authenticated non-regression pass on the real local `SA24D` roster and `G20` classroom when available, and the authenticated transport audit must explicitly confirm the canonical `/api/v1/apps/...` seam stayed unchanged.
- The full frontend suite is now green again after closing `PR-0235` and `PR-0236`.
- `ST-09-09` is done. The canonical local operator commands are `pdm run hemma-deploy` and `pdm run hemma-deploy-monitor`, while the on-host deploy script remains the single deploy/readiness source of truth.
- Shell quality is part of the normal repo gate now: `pre-commit` runs ShellCheck on staged shell scripts, and `pdm run lint` includes repo-wide `pdm run shellcheck-all`.
- Active docs guidance now uses `docs/reference/ref-development-changelog.md` as the append-only dump for removed handoff history, and the stale `REF-implementation-map-script-hub-v0-2` reference has been removed.
## Verification
- `pdm run lint` (pass; includes repo-wide `shellcheck-all`)
- `pdm run docs-validate` (pass after deleting `REF-implementation-map-script-hub-v0-2`, adding `REF-development-changelog`, compacting `.agents/handoff.md`, and aligning the handoff/changelog invariant in active guidance)
- `pdm run docs-validate` (pass after enriching `PR-0232` with the agreed boundary-first implementation shape, updating `PR-0229` to own post-`PR-0232` toolbar shortcut polish/alignment, and refreshing `.agents/handoff.md`)
- `pdm run docs-validate` (pass after tightening `PR-0232` around export-preparation flush semantics, guest checkpoint fingerprint dedupe, explicit guest/auth affordance rows, authenticated regression proof, and the register-now / import-later alignment with `PR-0221`)
- `pdm run docs-validate` (pass after adding the explicit `PR-0232` required quality gate for live guest proof plus authenticated `SA24D` / `G20` non-regression transport audit)
- `pdm run docs-validate` (pass after updating `PR-0232` and `.agents/handoff.md` with the required live `SA24D` / `G20` authenticated verification gate and transport-audit requirement)
- `pdm run docs-validate` (pass after documenting `PR-0233` as the narrow `ST-32-05` auth seam remediation task, cross-linking it from the story/epic/index, and refreshing `.agents/handoff.md`)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_guest_upgrade_handler.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_template_reuse.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_idempotency.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py -q` (pass; authenticated template reuse/remap seam plus route regression)
- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts` (pass; authenticated prompt and entry-shell non-regression)
- `pdm run fe-type-check` (pass)
- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` (expected fail before remediation; reproduces lost selected classroom on guest grouping entry and stale enabled `Sittplatser` affordance after classroom context is gone)
- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` (pass after the `PR-0234` fix; guest classroom context persists through grouping entry and `Sittplatser` disables correctly when classroom context is absent)
- Live authenticated API proof on 2026-04-07 against `http://127.0.0.1:8000/api/v1/apps/classroom.group-seating-studio/guest-upgrade` using the real local `SA24D` roster (`65d3f959-20ea-432d-a28b-0e970f9972ec`) and `G20` classroom (`36fe6e61-99b6-424b-a09f-1933aae88ed9`) with a non-toy seating draft plus export-backed checkpoint descriptor (pass; `200 OK`, roster/template marked `reused`, no conflicts)
- Live authenticated browser proof on 2026-04-07 against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` after injecting a non-toy guest snapshot backed by the real local `SA24D` / `G20` data into browser storage (pass; `guest-upgrade-modal` rendered and `guest-upgrade-error-message` count stayed `0`)
- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts` (pass; guest overview/shell parity plus public Smart composables)
- `pdm run fe-test -- --run src/views/apps/roomBuilderViewport.spec.ts src/views/apps/useRoomViewportZoom.spec.ts src/views/apps/components/RoomTemplateBuilderSurface.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts` (pass; `PR-0235` framed viewport contract + 100% cap across helper/composable/shared consumers)
- `pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts` (pass; `PR-0236` capability-gated roster overview spec realignment)
- `pdm run fe-type-check` (pass after the `PR-0235` helper/spec realignment)
- `pdm run fe-type-check` (pass after the `PR-0236` spec realignment)
- `pdm run fe-test` (pass; 145 files, 753 tests)
- Live local browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass for `PR-0235`; public builder modal rendered `builder-zoom-percent = 100%` and `room-builder-scroll-frame[data-overflow-anchor] = center` for a fresh small-room state; Playwright Chrome session was explicitly closed after the check)
- `pdm run docs-validate` (pass after implementing `PR-0236`, updating remediation task statuses, and refreshing `.agents/handoff.md`)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py` (pass; stateless public Smart handlers and public helper routes)
- Live public browser proof against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` with local backend on `http://127.0.0.1:8000` (pass; guest `Regler`, guest Smart drawer parity without `Historik`, and live `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run` `200 OK`)
- Live public browser proof for `PR-0234` against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass; seeded guest snapshot kept `selected_template_local_id = template-1` and `grouping_draft.template_local_id = template-1` after overview -> `Grupper`; a forced grouping-without-classroom state rendered `Sittplatser` disabled with title `Skapa eller välj först ett klassrum.`)
- Live production proof on Hemma (pass on 2026-04-07): `pdm run hemma-deploy` handed off detached remote PID `1243606`; the authoritative raw log `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log` shows commit `94be5c23bbfb8294278cf21d3f679ee693277f73` deployed, migrations applied, and seating-export smoke passed
## How to Run
```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts
pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts
pdm run pytest tests/unit/application/apps/classroom_planner/test_guest_upgrade_handler.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_template_reuse.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_idempotency.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py -q
pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts
pdm run fe-test
pdm run fe-type-check
pdm run docs-validate
```
## Known Issues / Risks
- Public guest mode is browser-owned and route-sensitive. Use `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` for the guest shell; if that route looks blank in one browser profile, clear the local `skriptoteket:classroom-planner:public-snapshot-id` pointer plus IndexedDB `skriptoteket_curated_apps` / `classroom_planner_guest_snapshots` before treating it as a code regression.
- `PR-0234`, `PR-0235`, and `PR-0236` are resolved locally and the frontend suite is green; the remaining risk is the pre-existing suppressed centered-shell runtime warning in `ClassroomPlannerView.spec.ts`, which still does not fail the suite.
- `ClassroomPlannerView.spec.ts` still emits the pre-existing suppressed runtime warning from `resolveHomeRosterId(...)` during one centered-shell test even though the suite passes; it was not part of `PR-0226`.
## Next Steps
- Keep `PR-0234` scoped to the now-green guest classroom-context fix and treat it as resolved locally unless a new regression disproves the recorded proof.
- Execute `PR-0232` after `PR-0234` as the remaining `ST-32-06` guest-mode bridge slice: guest local undo/redo parity, direct-download export, and account-only history/recovery affordance polish.
- Keep guest/public continuity honest in `PR-0232`: local undo/redo only, direct-download export only, and no fallback into authenticated export/history/recovery seams.
- During `PR-0232` verification, use the real local `SA24D` roster and `G20` classroom fixtures for the authenticated non-regression pass when they are available, and record the canonical `/api/v1/apps/...` transport audit explicitly in `.agents/handoff.md`.
- Return to `PR-0229` only after the guest-mode bridge slice. `PR-0229` now explicitly picks up any post-`PR-0232` toolbar shortcut polish/alignment and overflow discoverability cleanup without reopening the guest/auth boundary.
- Preserve the `PR-0233` seam shape while implementing `PR-0232`: later guest export/checkpoint continuity should keep feeding the existing authenticated `import` / `discard` / `postpone` prompt instead of adding a new compatibility lane.
