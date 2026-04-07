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
- Current lane: `EPIC-32` / `ST-32-07` through `ST-32-09` planning scaffold for landing entry hierarchy, showcase surfaces, and malformed-route recovery
- Production: Full Vue SPA
- Completed: `PR-0231`, `PR-0232`, `PR-0233`, `PR-0234`, `PR-0235`, and `PR-0236` are shipped on `main`; the public/export review follow-ups and Vitest path-normalization hardening are pushed; `ST-09-09` is done with the shipped Hemma deploy launcher/monitor path; ShellCheck is now part of pre-commit and `pdm run lint`; active docs guidance now has a canonical development changelog and the stale v0.2 implementation map has been removed
## Status
- `PR-0231` is shipped on `main` and its retained review follow-ups are fixed. Guest `Regler`, public solver-backed Smart, request streaming limits, persistence rollback, and helper-family throttle wiring are in place.
- `PR-0232` is shipped on `main` without reopening the guest/auth boundary:
  - guest undo/redo moved into a small guest-only helper and is wired through the shared shortcut composable at the guest/auth workspace-shell seam
  - guest export keeps the shared split-button UI but now uses dedicated public direct-download helpers/routes instead of the authenticated export-job/Vault flow
  - guest export writes deduped export-backed checkpoint descriptors back into the browser snapshot and keeps them outside guest history / `Use history` semantics
  - authenticated export/history transport remains on the canonical `/api/v1/apps/...` job/history seam
- `PR-0232` frontend coverage includes both guest grouping and guest seating direct-export composables, plus focused guest history and shell shortcut tests.
- Post-review `PR-0232` checkpoint drift hardening is shipped: guest export checkpoints are derived from the exact frozen snapshot sent to the public export helper, then appended later even if the guest mutates the draft or switches drafts before the download resolves.
- `PR-0233` is shipped as the narrow `ST-32-05` remediation slice. The authenticated guest-upgrade seam now compares guest templates to real persisted template geometry, deterministically remaps reused-template seat ids through a dedicated helper module, and no longer reproduces the old non-toy template-bearing `500` on `/api/v1/apps/classroom.group-seating-studio/guest-upgrade`.
- `PR-0234` is shipped. The assessed root cause was the public guest overview -> grouping seam dropping the selected classroom by opening grouping with `templateId = null`, plus stale pending template refs keeping `Sittplatser` visually enabled after live classroom context was gone. A small helper module now centralizes the live guest classroom-context rule, overview -> grouping preserves the selected classroom, and the guest shell disables `Sittplatser` from real live context rather than stale pending refs.
- `PR-0235` is shipped. The shared viewport helper keeps the framed-surface fit model across builder / seating / rules, fit-to-view is explicitly capped at `100%`, and the pure helper seam now has focused coverage so the repo no longer relies on stale pre-frame numbers in `useRoomViewportZoom.spec.ts`.
- `PR-0236` is shipped. The stale isolated roster-overview spec now passes `showActions` explicitly when asserting the visible action footer, also proves the hidden-footer case when actions are disabled, and keeps class-list import inside the create/edit workflow.
- `ST-32-07` is now scaffolded as the next `EPIC-32` follow-up:
  - the planning hierarchy is corrected so `EPIC-32` remains the container and the follow-up work now lives as explicit stories `ST-32-07`, `ST-32-08`, and `ST-32-09`
  - `ST-32-07` owns landing header/hero entry hierarchy plus the required mockup-first alignment pass through `PR-0237` and `PR-0238`
  - `ST-32-08` owns the featured public-app showcase and authenticated-value preview surface through `PR-0239`
  - `ST-32-09` owns catch-all route recovery and malformed public-path guidance through `PR-0240`
- `PR-0237` competitive mockup round has begun with `docs/mockups/st-32-07-public-landing-discoverability/designer-cascade.html` demonstrating the calm header, strong Klassrumskartan hero CTA, and non-card typographic layout.
- The review follow-up pass that closed the public export/Vitest footguns is also shipped on `main`:
  - `public_seating_export.py` now imports and uses `validation_error(...)` correctly
  - direct handler tests cover invalid public PDF branches and route tests assert forwarded handler args
  - the autosave/history spec now proves exactly one draft PATCH hits the draft endpoint and zero smart-rule PATCHes leak into that contract
  - the Vitest wrapper now normalizes repo-root and app-local paths through `frontend/apps/skriptoteket/scripts/vitest-run.mjs`
- The full backend and frontend suites are green from the pushed tree.
- `ST-09-09` is done. The canonical local operator commands are `pdm run hemma-deploy` and `pdm run hemma-deploy-monitor`, while the on-host deploy script remains the single deploy/readiness source of truth.
- Shell quality is part of the normal repo gate now: `pre-commit` runs ShellCheck on staged shell scripts, and `pdm run lint` includes repo-wide `pdm run shellcheck-all`.
- Active docs guidance now uses `docs/reference/ref-development-changelog.md` as the append-only dump for removed handoff history, and the stale `REF-implementation-map-script-hub-v0-2` reference has been removed.
## Verification
- `pdm run lint` (pass on pushed tree after the public export/OpenAPI-safe route follow-up)
- `pdm run typecheck` (pass on pushed tree)
- `pdm run docs-validate` (pass on pushed tree)
- `pdm run fe-lint` (pass on pushed tree)
- `pdm run fe-type-check` (pass on pushed tree)
- `pdm run fe-test` (pass on pushed tree; 149 files, 771 tests)
- `pdm run test` (pass on pushed tree; 1258 passed, 91 deselected)
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
- `pnpm -C frontend/apps/skriptoteket exec vitest run src/views/apps/classroomPlannerGuestDraftHistory.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/classroomPlannerGuestSnapshotMapping.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/classroomPlannerGuestDraftWorkspace.spec.ts` (pass; guest local history, grouping/seating public export flows, guest shell parity, checkpoint dedupe, and shared shortcut shell coverage)
- `pnpm -C frontend/apps/skriptoteket exec vitest run src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts` (pass after review feedback; 8 tests including in-flight draft mutation and draft-switch races to prove export checkpoints are persisted from the exact exported snapshot rather than the later UI state)
- `pdm run pytest tests/unit/web/test_public_apps_classroom_planner_exports.py tests/unit/web/apps/classroom_planner/test_grouping_export_job_api.py tests/unit/web/apps/classroom_planner/test_seating_export_job_api.py` (pass; new public export routes plus authenticated export-job non-regression)
- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` (expected fail before remediation; reproduces lost selected classroom on guest grouping entry and stale enabled `Sittplatser` affordance after classroom context is gone)
- `pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` (pass after the `PR-0234` fix; guest classroom context persists through grouping entry and `Sittplatser` disables correctly when classroom context is absent)
- Live authenticated API proof on 2026-04-07 against `http://127.0.0.1:8000/api/v1/apps/classroom.group-seating-studio/guest-upgrade` using the real local `SA24D` roster (`65d3f959-20ea-432d-a28b-0e970f9972ec`) and `G20` classroom (`36fe6e61-99b6-424b-a09f-1933aae88ed9`) with a non-toy seating draft plus export-backed checkpoint descriptor (pass; `200 OK`, roster/template marked `reused`, no conflicts)
- Live authenticated browser proof on 2026-04-07 against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` after injecting a non-toy guest snapshot backed by the real local `SA24D` / `G20` data into browser storage (pass; `guest-upgrade-modal` rendered and `guest-upgrade-error-message` count stayed `0`)
- Live public browser proof on 2026-04-07 against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` for `PR-0232` (pass; created guest roster `PR 0232 Gästklass`, grouping shell showed shared export affordance while history stayed hidden, `Meta+Z` changed group-count `5 -> 4`, `Meta+Shift+Z` restored `5`, default export downloaded `pr-0232-gästklass-gruppindelning.xlsx`, guest transport hit only `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/export`, no network `undo` / `redo` requests were emitted, and IndexedDB snapshot `07436e9b-fb99-4236-96c1-0755ec1e1068` kept exactly one export checkpoint after repeated export)
- Live authenticated browser non-regression on 2026-04-07 against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` for `PR-0232` (pass; logged in with bootstrap superuser, imported the guest snapshot through the canonical `import` prompt, selected imported roster `PR 0232 Gästklass`, grouping export downloaded through existing authenticated job flow `POST /api/v1/apps/classroom.group-seating-studio/drafts/grouping/beb301c1-67e0-492f-8f7f-c659c0c1dff8/exports/jobs` + `GET /api/v1/apps/classroom.group-seating-studio/grouping/exports/jobs/.../download`, and authenticated history transport still used `POST /api/v1/apps/classroom.group-seating-studio/drafts/beb301c1-67e0-492f-8f7f-c659c0c1dff8/undo`)
- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts` (pass; guest overview/shell parity plus public Smart composables)
- `pdm run fe-test -- --run src/views/apps/roomBuilderViewport.spec.ts src/views/apps/useRoomViewportZoom.spec.ts src/views/apps/components/RoomTemplateBuilderSurface.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts` (pass; `PR-0235` framed viewport contract + 100% cap across helper/composable/shared consumers)
- `pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts` (pass; `PR-0236` capability-gated roster overview spec realignment)
- `pdm run fe-type-check` (pass after the `PR-0235` helper/spec realignment)
- `pdm run fe-type-check` (pass after the `PR-0236` spec realignment)
- `pdm run fe-test` (pass; 149 files, 771 tests)
- Live local browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass for `PR-0235`; public builder modal rendered `builder-zoom-percent = 100%` and `room-builder-scroll-frame[data-overflow-anchor] = center` for a fresh small-room state; Playwright Chrome session was explicitly closed after the check)
- `pdm run docs-validate` (pass after implementing `PR-0236`, updating remediation task statuses, and refreshing `.agents/handoff.md`)
- `pdm run docs-validate` (pass after scaffolding `ST-32-07` and `PR-0237` through `PR-0240`)
- Live local browser proof on `docs/mockups/st-32-07-public-landing-discoverability/designer-cascade.html` (pass; layout verified according to PR-0237 rules)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py` (pass; stateless public Smart handlers and public helper routes)
- Live public browser proof against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` with local backend on `http://127.0.0.1:8000` (pass; guest `Regler`, guest Smart drawer parity without `Historik`, and live `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run` `200 OK`)
- Live public browser proof for `PR-0234` against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass; seeded guest snapshot kept `selected_template_local_id = template-1` and `grouping_draft.template_local_id = template-1` after overview -> `Grupper`; a forced grouping-without-classroom state rendered `Sittplatser` disabled with title `Skapa eller välj först ett klassrum.`)
- Live production proof on Hemma (pass on 2026-04-07): `pdm run hemma-deploy` handed off detached remote PID `1243606`; the authoritative raw log `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log` shows commit `94be5c23bbfb8294278cf21d3f679ee693277f73` deployed, migrations applied, and seating-export smoke passed
## How to Run
```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run fe-type-check
pdm run pytest tests/unit/web/test_public_apps_classroom_planner_exports.py tests/unit/web/apps/classroom_planner/test_grouping_export_job_api.py tests/unit/web/apps/classroom_planner/test_seating_export_job_api.py
pdm run fe-test -- --run src/views/apps/classroomPlannerGuestDraftHistory.spec.ts src/views/apps/usePublicGroupingExportFlow.spec.ts src/views/apps/usePublicSeatingExportFlow.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/classroomPlannerGuestSnapshotMapping.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/classroomPlannerGuestDraftWorkspace.spec.ts
pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts
pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestGroupingContext.spec.ts src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts
pdm run pytest tests/unit/application/apps/classroom_planner/test_guest_upgrade_handler.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_template_reuse.py tests/unit/application/apps/classroom_planner/test_guest_upgrade_idempotency.py tests/unit/web/apps/classroom_planner/test_guest_upgrade_api.py -q
pdm run fe-test -- --run src/views/apps/useClassroomPlannerGuestUpgrade.spec.ts src/views/apps/ClassroomPlannerEntryView.spec.ts
pdm run fe-test
pdm run docs-validate
```
## Known Issues / Risks
- Public guest mode is browser-owned and route-sensitive. Use `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` for the guest shell; if that route looks blank in one browser profile, clear the local `skriptoteket:classroom-planner:public-snapshot-id` pointer plus IndexedDB `skriptoteket_curated_apps` / `classroom_planner_guest_snapshots` before treating it as a code regression.
- `PR-0232` live proof covered guest grouping export plus authenticated non-regression. Guest seating direct-download is covered by backend route tests and the new `usePublicSeatingExportFlow.spec.ts`, but it was not manually live-driven in the browser during this session.
- `PR-0234`, `PR-0235`, and `PR-0236` are resolved locally and the frontend suite is green; the remaining risk is the pre-existing suppressed centered-shell runtime warning in `ClassroomPlannerView.spec.ts`, which still does not fail the suite.
- `ClassroomPlannerView.spec.ts` still emits the pre-existing suppressed runtime warning from `resolveHomeRosterId(...)` during one centered-shell test even though the suite passes; it was not part of `PR-0226`.
## Next Steps
- Keep `PR-0232` scoped to the now-implemented guest/auth boundary split unless review finds a concrete regression: local guest history only, public direct-download export only, and no fallback into authenticated export/history/recovery seams.
- Start `ST-32-07` with `PR-0237` only: review `.agents/rules/045-huleedu-design-system.md`, `skriptoteket-frontend-specialist`, and `brutalist-academic-ui`, then create the canonical `docs/mockups/st-32-07-public-landing-discoverability/index.html` preview before touching production landing code.
- Run `PR-0237` as a competitive mockup round for the lead web designers: each designer should post independent files under `docs/mockups/st-32-07-public-landing-discoverability/`, avoid editing or studying another designer's work unless explicitly told to do so, and expect the best overall submission to be promoted to blueprint.
- After the mockup is agreed, complete `ST-32-07` with `PR-0238`, then move into `ST-32-08` for the below-the-fold showcase/authenticated-preview work through `PR-0239`.
- Treat `ST-32-09` / `PR-0240` as the final repair story for unmatched-route handling so malformed `/public/<app-id>` paths recover visibly without changing the canonical `/public/apps/:appId` contract.
- If follow-up polish is needed, return to `PR-0229` for toolbar overflow/discoverability work without reopening the guest/auth transport boundary.
- Return to `PR-0229` only after the guest-mode bridge slice. `PR-0229` now explicitly picks up any post-`PR-0232` toolbar shortcut polish/alignment and overflow discoverability cleanup without reopening the guest/auth boundary.
- Preserve the `PR-0233` seam shape while implementing `PR-0232`: later guest export/checkpoint continuity should keep feeding the existing authenticated `import` / `discard` / `postpone` prompt instead of adding a new compatibility lane.
