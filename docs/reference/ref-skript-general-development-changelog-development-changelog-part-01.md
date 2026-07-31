---
type: reference
id: REF-SKRIPT-GENERAL-development-changelog-PART-01
title: Development changelog — part 01
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
root: REF-SKRIPT-GENERAL-development-changelog
part: 1
---

## Overview

Append-only development log and repo long-term memory for compacted handoff history.

Rule:
- When compacting `.codex/handoff.md`, move non-session-vital handoff history here first.
- Paste the removed handoff content directly with minimal reshaping.

## Facts And Semantics

### Source: 2026-06-13 PR-0349 Live Proof Blocker

- `PR-0349` added a retained authenticated browser proof harness for the
  transcript parity path and proved the local HuleEdu/Skriptoteket stacks can
  reach the transcript lane after DB migrations are applied.
- HuleEdu shared PostgreSQL verification passed for all lifecycle targets, and
  Skriptoteket `pdm run dev-stack db-upgrade` completed cleanly.
- The complete progress/cancel/save/overlay/replay/download/Mina filer path is
  blocked before job creation: live Sir Convert returns
  `auth_invalid_internal_identity` with
  `invalid_internal_identity_signature` for the local Gateway-signed submit.
- Retained sanitized evidence:
  `.artifacts/playwright-pr-0349-transcript-parity-live/20260613T134340Z/`,
  whose `proof-summary.json` exposes
  `blocker_kind=sir_convert_internal_identity_rejected` plus the sanitized
  error code and reason.
- Root cause evidence: local HuleEdu internal-identity public-key fingerprint
  differs from the Sir Convert prod trusted public-key fingerprint. Do not
  retry the same local proof until the HuleEdu/Sir Convert signer/trust lane is
  reconciled or a sanctioned Hemma/prod browser proof lane is provided.

### Source: 2026-05-06 handoff compaction dump

Moved from `.codex/handoff.md` while adding `PR-0305` so the live handoff stays under the
repo line-count limit.

### Previous Status

- Added `ST-SKRIPT-11-26` and `TASK-SKRIPT-11-26-01` under `EPIC-SKRIPT-11` for the palette/token refresh.
- Updated canonical token source `src/skriptoteket/web/static/css/huleedu-design-tokens.css`:
  Deep Navy `#082B4C`, Warm Terracotta `#C94F32`, Verdigris Teal `#3F7F78`, light canvas/paper
  `#FAFAF6`, critical burgundy `#4D1521`.
- Added semantic aliases for brand, text, border, action, primary button, and surface roles.
- Kept `burgundy` as a deprecated compatibility alias for the critical channel; new action state
  uses `action`.
- Updated Tailwind bridge with `paper`, `terracotta`, `action`, `critical`, and
  `button-primary-text`.
- Updated shared primitives: `btn-primary`, `btn-cta`, focus rings, planner selected states,
  danger buttons, toast failure, dense buttons, segmented toggles, toggle switches, small-screen
  active rows/tabs/rules, share/export create buttons, room-seat selected state, and roster import
  drag-active state.
- Guarded filled selected selectors so selected teal controls keep light text, including nested
  labels/icons in the desktop Översikt Dela scope selector.
- Kept warning amber/ochra and critical/error-family separate; terracotta and teal are not warning
  colors.
- Reverted canvas/paper from the initial warmer `#F7F3EC` idea back to the lighter `#FAFAF6` to
  avoid red/saturated page backgrounds behind white panels.
- Updated `.codex/rules/045-huleedu-design-system.md`, `ADR-SKRIPT-0032`, the frontend design-system
  codemap, `docs/index.md`, and `EPIC-SKRIPT-11`.
- Added the surface-cohesion rule: light canvas is the uniform base; avoid stacked white-on-canvas
  panels and use light row/object highlights instead.
- Replaced remaining live SPA burgundy action/focus/accent drift with `action` where functional,
  `critical` where destructive/error, and terracotta only for small brand/editorial accent.
- Updated local logo SVG/PNG assets, verification email CTA, Klassrumskartan share/poster/PDF
  renderer literals, docx script colors, and landing SVG assets toward the new palette.
- Tightened the share/export hierarchy after visual review: selected scopes keep teal fill/light
  text, `Skapa länk` is secondary teal outline/text with `IconLink2`, and the Dela panels/file rows
  use canvas-toned surfaces instead of white-on-canvas patchwork.
- Follow-up surface pass replaced visible white-on-canvas panel shells with `bg-panel` /
  `bg-panel-muted`: dashboard/catalog cards, admin lists, suggestion forms, planner top panel,
  workspace toolbar, overview setup panel, grouped/student panels, rules summary panels, phone
  sheets/trays, modals/drawers, and shared planner button rails. Inputs and actual room/canvas
  objects intentionally remain white.
- Modal-shell follow-up added opaque `--huleedu-modal` / `--surface-modal` / `bg-modal` for modal,
  dialog, popover, drawer, and sheet shells over overlays. In-page panels still use translucent
  `bg-panel`; text fields, textareas, room objects, and isolated previews keep deliberate white
  contrast.
- Toast color follow-up: transient `failure` toasts now use warm terracotta (`bg-terracotta/90`)
  instead of critical burgundy, while destructive and blocking inline errors remain on
  critical/error-family channels.

### Previous Verification

- Toast color follow-up: `pdm run fe-build` passed; existing large chunk-size warnings remain.
- Toast color follow-up: `pdm run docs-validate` passed.
- Toast color follow-up: scoped `git diff --check -- frontend/apps/skriptoteket/src/assets/main.css
  src/skriptoteket/web/static/css/huleedu-design-tokens.css
  docs/reference/ref-toast-system-messages.md .codex/rules/045-huleedu-design-system.md
  docs/backlog/stories/story-13-01-toast-system-primitives-spa.md
  docs/backlog/prs/pr-0295-st-11-26-huleedu-palette-token-refresh.md
  docs/backlog/prs/pr-0299-st-13-02-auth-and-critical-action-feedback-toast-audit.md` passed.
- `PR-0300` checks passed: focused Klassrumskartan backend tests (`42 passed`), fixed-seat domain
  tests (`4 passed`), `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`,
  `pdm run fe-lint`, route-shell Vitest (`4 passed`), `pdm run docs-validate`, and
  `git diff --check`.
- Fixed-seat rules UX parity check passed: `pdm run fe-test -- --run
  classroomPlannerSmartRuleActions PlannerRulesWorkspacePane PlannerRulesMapCanvas` passed
  (3 files, 19 tests), `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run docs-validate`, and
  `git diff --check` passed. In-app browser was reachable through browser-use and showed the
  HuleEdu login ceremony for Skriptoteket; no credentials were submitted.
- Fixed-seat visual preview follow-up passed: pending fixed-seat authoring now highlights the
  pending student, marks the pending seat with a dashed lock and student-seat label, and shows a
  compact `Fast plats` marker when the selected student is in the unassigned list. Focused Vitest,
  `fe-type-check`, `fe-lint`, and `git diff --check` passed.
- Fixed-seat classroom-canvas deselection follow-up passed: clicking the already selected pending
  seat emits seat deselection, and clicking the selected seated student when no pending seat exists
  emits student deselection. Focused Vitest now covers 20 tests; `fe-type-check`, `fe-lint`, and
  `git diff --check` passed.
- Fixed-seat preview polish follow-up passed: binding pills now use neutral matching styling, the
  canvas pending fixed-seat preview keeps only the lock marker without the extra text card, and the
  rules map toggle orders `Klassrumsvy` before `Planeringskarta` while preserving the classroom
  default. Focused Vitest, `fe-type-check`, `fe-lint`, and `git diff --check` passed.
- Rules workspace tool-rail follow-up passed: `Skapa/Spara regel` and `Rensa markering` now live in
  a bottom action slot inside the fixed-height rail, so fixed-seat preview content can
  appear/disappear without moving the buttons. The layout remains CSS-owned (`flex`/`mt-auto` plus
  the focused `klassrumskartan-rules-workspace.css` rules); no JS sizing or sticky logic was added.
  Focused Vitest, `fe-type-check`, `fe-lint`, `fe-build`, `docs-validate`, `handoff-validate`, and
  `git diff --check` passed; `pdm run dev-stack ps` showed web/worker healthy plus db/frontend up.
  In-app browser was available through `browser-use`/Node REPL but remained on the HuleEdu login
  form, so no credentialed visual action was taken.
- Rules workspace geometry follow-up passed: the fixed-seat planning-map prompt keeps its locked
  wording while using `bg-canvas`, the active-rules summary and tool/map row now have a normal
  workspace gutter, sticky behavior moved to the whole rules tool column, and the side rail
  reserves a fixed 480px desktop height so dynamic rule controls do not resize the panel. New CSS
  lives in the focused `klassrumskartan-rules-workspace.css` import. Focused Vitest,
  `fe-type-check`, `fe-lint`, `docs-validate`, and `git diff --check` passed.
- `pdm run fe-test -- src/App.spec.ts src/components/layout/AuthLayout.spec.ts
  src/views/apps/classroomPlannerPublicShareFlow.spec.ts
  src/views/apps/classroomPlannerShareFlow.spec.ts
  src/views/apps/classroomPlannerRouteShellWorkspace.spec.ts src/components/vault/VaultPanel.spec.ts`
  passed: 6 files, 19 tests.
- `pdm run fe-type-check` passed.
- `pdm run fe-lint` passed.
- `pdm run fe-build` passed; existing large chunk-size warnings remain.
- `pdm run docs-validate` passed.
- `pdm run handoff-validate` passed.
- `git diff --check` passed.

### Source: 2026-04-12 handoff compaction dump

Moved from `.codex/handoff.md` while preparing `ST-28-08` / `PR-0257` as the next
provider-contract gate after approved `PR-0256`.

- Reviewer advice acted on: `frontend/apps/skriptoteket/src/stores/ai.ts` now fails closed while
  `auth.aiPolicy` is missing, and `frontend/apps/skriptoteket/src/stores/ai.spec.ts` freezes that
  missing app-local AI bootstrap does not allow remote providers.
- `PR-0251` continuation slice is implemented: `GET /api/v1/profile/app-continuation` returns
  runtime `ai_policy` plus profile AI preferences, `useAuthStore.bootstrap()` performs HuleEdu
  session first and app-local continuation second, and editor AI chat/completions/edit-ops no
  longer read AI preferences from local `Session` fields.
- `PR-0252` is implemented: direct protected entry, app-local `401` recovery, and top-level
  `/auth/login?next=...` return preserve the dedicated auth-entry contract on the HuleEdu-owned
  session model. Live proof uses the real backend app-continuation route, signed HuleEdu request
  context, DB projection, and Vite `/api` proxy. Shared proof helpers now live in
  `scripts/_playwright_huleedu_auth.py`.
- Independent `skriptoteket_reviewer` pass for `PR-0252` approved the implementation with no
  actionable findings. Residual note: the live proof covers canonical `/editor`; richer query/hash
  destinations are covered by focused Vitest.
- `PR-0253` preserved local RBAC by resolving signed HuleEdu subjects to existing Skriptoteket
  `User` projections and enforcing local `User.role`; HuleEdu roles/grants remain context metadata,
  not Skriptoteket admin/contributor/superuser assignment.
- Post-`PR-0253` auth observability rule: do not recreate `skriptoteket_active_sessions` from local
  state. Future gauges/counters should measure HuleEdu signed-context verification/projection
  outcomes or local RBAC inventory such as `skriptoteket_users_by_role` when explicitly enabled.
- `PR-0251` must preserve Skriptoteket-local role, profile, AI policy, and app authorization
  semantics without reinstating local browser auth authority, bearer storage, or direct HuleEdu
  Identity calls.
- `REV-PR-0251` retained re-review is approved; `PR-0254` remains for Docker-first realm-aware
  cross-app proof after the new identity-realm path.
- `HomeView.vue` / `HomeView.spec.ts` had pre-existing local changes before this docs lane; keep
  them separate from EPIC-28 scaffolding.
- Public guest mode remains browser-owned and route-sensitive; clear local public guest storage
  before treating a stale guest state as an auth-cutover regression.
- `REV-PR-0253` is approved; `PR-0253` / `ST-28-03` are done.

### Source: 2026-04-10 handoff compaction dump

Moved from `.codex/handoff.md` during EPIC-28 shared-auth consumer migration scaffolding.

- The previous handoff contained the full `PR-0231` through `PR-0249` implementation and proof
  history. That history remains durable in this changelog and in the corresponding backlog records;
  the active handoff was reduced back to the current decision points and executable next steps.
- Before compaction, `.codex/handoff.md` recorded that `REV-EPIC-28` is approved, `ST-32-10` /
  `PR-0242` owns the dedicated `/auth/login` route contract, and the remaining runtime blocker for
  EPIC-28 was HuleEdu host/session truth.
- The active state changed on 2026-04-10: HuleEdu has accepted ADR-SKRIPT-0039 and created the
  provider-conformance + consumer-handoff lane in `ST-01-03` / `TASK-0308`, so Skriptoteket now
  scaffolds consumer migration PR tasks under EPIC-28 instead of creating a duplicate epic.

### Source: 2026-04-09 handoff compaction dump

Moved from `.codex/handoff.md` during task-draft bookkeeping for `PR-0248` / `PR-0249`.

- `Keep PR-0232 scoped to the now-implemented guest/auth boundary split unless review finds a concrete regression: local guest history only, public direct-download export only, and no fallback into authenticated export/history/recovery seams.`
- `Preserve the PR-0233 seam shape while implementing PR-0232: later guest export/checkpoint continuity should keep feeding the existing authenticated import / discard / postpone prompt instead of adding a new compatibility lane.`
- `PR-0248` freezes the shared planner UX correction package for silent recovered export re-entry, bounded sticky Regler rail behavior, and removal of the redundant VÄLJ EN KLASSLISTA overview label.`
- `PR-0249` freezes the public-host reconciliation package for one singular login-first blocked state with approved Logga in / Skapa konto copy and action hierarchy.`
- `REV-PR-0248` and `REV-PR-0249` now exist as retained review records with initial `changes_requested` findings; the PR drafts were tightened around export-recovery truth, guest controller/view seam ownership, and auth action-target proof before implementation.`

### Source: 2026-04-07 handoff compaction dump

Moved from `.codex/handoff.md` during handoff cleanup.

### Previous Snapshot

- Date: 2026-04-07
- Branch: `main` + local changes
- Current lane: `ST-32-06` guest browser-workspace parity and continuity
- Production: Full Vue SPA
- Completed: `PR-0226`, `PR-0227`, and `PR-0228` are now shipped and docs-closed; `EPIC-34` is now docs-closed after `ST-34-01`, `ST-34-02`, and `PR-0230`; `ST-09-04` is now closed as a perimeter-hardening backfill/current-state record

### Previous Status

- `EPIC-34` is now docs-closed and `REV-EPIC-34` remains approved. `ST-34-01` backfills the already-shipped target-based review workflow cutover and legacy planning-doc retirement, while `ST-34-02` and `PR-0230` closed the remaining historical review-record migration lane under `REF-SKRIPT-DECISIONS-review-workflow-for-backlog-items-and-retained-decision-records`.
- `ST-32-06` docs are now re-shaped around the agreed guest/auth boundary: `ADR-SKRIPT-0080` freezes that guest parity includes `Regler`, the expandable Smart settings drawer, and solver-based Smart runs, while history-based Smart and `Use history` stay account-only. `PR-0223` is now docs-closed around the shipped public browser-workspace baseline, and the remaining guest-mode work is split into `PR-0231` and `PR-0232`.
- `PR-0231` is now implemented locally on top of that boundary and is the active session outcome: guest `Regler` is enabled in the shared public planner shell, guest Smart grouping/seating now call new stateless public helper routes, and the guest Smart drawers keep parity while hiding account-only `Historik` / `Use history`.
- The follow-up `REV-PR-0231` findings are now fixed locally too: reused guest grouping drafts now recontextualize to the newly selected classroom before persistence, the public Smart helper enforces request-size limits while streaming instead of after full buffering, and guest Smart grouping/seating roll back the optimistic solver result if browser snapshot persistence is blocked.
- The final `REV-PR-0231` follow-up is fixed locally as well: the live DI wiring no longer bakes `PublicHelperThrottleProtocol` to the generic import-preview limits. The shared throttle now accepts helper-family limits per request, so import-preview still honors `PUBLIC_HELPER_RATE_LIMIT_*` while public Smart honors `PUBLIC_HELPER_SMART_RUN_*` in both enforcement and emitted `429` metadata.
- `REV-ST-09-09` is approved, `ADR-SKRIPT-0081` is accepted, and `ST-09-09` is now done. The repo now ships `pdm run hemma-deploy` and `pdm run hemma-deploy-monitor`, the canonical runbook path uses the detached launcher, and the on-host deploy script remains the single source of deploy/readiness truth.
- The live April 7, 2026 Hemma proof for that lane is now recorded: `pdm run hemma-deploy` handed off detached remote PID `1243606`, wrote the authoritative raw log to `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log`, and that raw log shows commit `94be5c23bbfb8294278cf21d3f679ee693277f73` deployed, migrations applied, and the seating-export smoke passing with artifacts under `.artifacts/pr-0146-seat-export-cutover-20260407-092323/`.
- The final operator polish from the live run is now reflected locally too: `scripts/hemma_deploy_monitor.sh` replays existing milestone/failure lines before following new output, and `scripts/hemma_deploy_start.sh` now says the detached handoff succeeded rather than implying the whole deploy already passed.
- The new backend seam for `PR-0231` lives under `src/skriptoteket/web/api/v1/public_apps_classroom_planner_smart.py` with stateless application handlers in `src/skriptoteket/application/curated_apps/classroom_planner/handlers/public_smart_grouping.py`, `public_smart_seating.py`, and `public_smart_run_support.py`. Dedicated smart-run abuse-control settings now live in `src/skriptoteket/config.py`.
- The guest frontend wiring for `PR-0231` now spans `frontend/apps/skriptoteket/src/views/apps/useClassroomPlannerGuestController.ts`, `ClassroomPlannerGuestOverviewView.vue`, `ClassroomPlannerGuestWorkspaceShell.vue`, `classroomPlannerGuestDraftSession.ts`, and the new public Smart composables `usePublicSmartGroupingRun.ts` / `usePublicSmartSeatingRun.ts`.
- `REV-PR-0231` now acts as the retained ruthless review gate for both remaining `ST-32-06` gap-bridging PRs. It reviews `PR-0231` and `PR-0232` as one guest-boundary package so solver-based Smart parity, local undo/redo/export continuity, and the account-only history boundary are judged together rather than drifting apart.
- `REV-PR-0231` is now approved after re-review. The retained planning gate now freezes that `PR-0231` must ship real public solver-backed guest Smart for both `Grupper` and `Sittplatser`, while `PR-0232` must use dedicated public direct-download export routes with explicit abuse-control and validation expectations from `ADR-SKRIPT-0079`.
- Docs-closeout debt is reduced: `EPIC-34` is now marked done, `ST-09-04` is now marked done as an already-implemented perimeter-hardening backfill, `REV-EPIC-29` is now approved, and older retained review docs with re-review/addendum approval history no longer contradict their frontmatter statuses.
- `PR-0228` is now closed as the bounded `ST-SKRIPT-29-11` planner-shell follow-up. The local implementation stays on the corrected scroll model rather than the rejected bounded-pane model: on the authenticated Vite route with the real `SA24D` / `G20` workspace, `main.auth-main-content` is again the primary vertical scroller, the large top panel can scroll away, the toolbar becomes the sticky operational band, and both grouping/seating class-list rails are capped to `480px` with internal list-body overflow.
- `REV-PR-0228` is now approved on an explicit close-out boundary: the retained live browser proof remains the authenticated real-data lane, while guest/auth parity is enforced through the shared shell implementation plus focused guest/auth shell specs instead of a second retained guest browser script.
- `TASK-SKRIPT-29-11-02` is now the next active `ST-SKRIPT-29-11` toolbar follow-up: freeze deliberate desktop-first breakpoint behavior for the shared planner toolbar, keep the bar one row, move `undo` / `redo` into overflow first, move `Börja om` next, and add canonical undo/redo keyboard shortcuts so lost always-visible buttons do not become lost capabilities.
- Review docs now use the new target-based shape from the `skill-repository` model: `REV-EPIC-29` is back to the epic decision record, while `PR-0226`, `PR-0227`, `PR-0228`, and `TASK-SKRIPT-29-11-02` each have their own retained review doc under `docs/backlog/reviews/`.
- The retained review workflow docs are now explicit that ADRs are reviewed through the governing epic/story/PR review record via `adrs:`, while one primary target still drives the review filename and id.
- The planner follow-up review gates now live at `docs/backlog/reviews/review-pr-0228-planner-workspace-shell-breakpoint-and-overflow-contract.md` and `docs/backlog/reviews/review-pr-0229-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md`, with the existing repomix bundles still at `.codex/repomix_packages/repomix-pr-0228-workspace-contract-review.xml` and `.codex/repomix_packages/repomix-pr-0229-toolbar-breakpoint-overflow-review.xml`.
- Legacy planning docs are now deprecated and treated as historical records only.
- The shared planner geometry is now expressed through named CSS primitives in `frontend/apps/skriptoteket/src/assets/main.css` and consumed from `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`. `PlannerWorkspaceShell.vue`, `ClassroomPlannerGuestWorkspaceShell.vue`, `PlannerStudentPool.vue`, `GroupBoard.vue`, `GroupCard.vue`, and `RoomCanvas.vue` now consume those shared primitives instead of carrying the old mixed `xl:` utility contract.
- Grouping now matches the corrected product shape locally: the board stays on the main page/workspace scroll path, the left rail stays a `480px` working surface, the student list scrolls inside that rail, and the rail remains visually attached below the sticky toolbar as the page scrolls.
- Seating now follows the same high-level contract locally: the top panel can scroll away, the toolbar becomes sticky, the class-list rail is capped at `480px` with internal list-body overflow, and the room canvas remains the primary seating surface inside the page/workspace scroll path.
- The external review package for that task now lives at `.codex/repomix_packages/repomix-pr-0228-workspace-contract-review.xml` and bundles the current docs, shared planner shell files, pane/layout seams, focused specs, and the existing Playwright proof lane.
- The docs are now explicit about the geometry/proof guardrails too: `EPIC-SKRIPT-29`, `ST-29-03`, `ST-SKRIPT-29-11`, and `PR-0228` now state that planner-family geometry is CSS-owned, that `PR-0228` must prove the failing pre-`xl` band, and that the seating proof must verify rail-to-right-lane alignment during deeper canvas scrolling.
- The remaining risk surface is no longer “make the pane taller”; it is keeping the new page-scroll model stable across resize bands and toolbar/rail stickiness without reintroducing nested board scrollers or brittle wrapper math.
- Older story ownership is now explicit in docs: `docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md` now freezes the desktop student-pool/class-list rail as a locally sticky side surface with a fixed header and scrolling list body, and `docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md` now reinforces that the sticky rail is part of the shipped grouping/seating desktop composition rather than an incidental implementation detail.
- `scripts/playwright_pr_0227_group_board_height_contract_check.py` is now auth-only for live proof and uses the real `SA24D` / `G20` workspace. It no longer verifies the rejected “internal board-lane scroll” model; it now proves page/workspace scroll past the top panel, sticky toolbar + rail, fixed `480px` class-list rails, and the existing grouping card-floor contract.
- `PR-0226` is implemented locally across the shared planner shell and grouping layout contract. Shared wrapper/layout logic now lives in `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceModeSurface.vue` and `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`, with both `PlannerWorkspaceShell.vue` and `ClassroomPlannerGuestWorkspaceShell.vue` consuming the same sticky toolbar + pane-shell contract.
- `PR-0227` is now done locally as the next bounded `ST-SKRIPT-29-11` follow-up: `frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts`, `frontend/apps/skriptoteket/src/views/apps/components/GroupCard.vue`, and the focused component specs now freeze a desktop-only card-floor contract where the empty/default 4-group 2x2 board measures exactly `480px` at `1440x900`, while the underlying `234px` card rule persists as a desktop `min-height` floor rather than a universal hard cap once students are assigned.
- Grouping layout stabilization is live locally: `PlannerGroupingWorkspacePane.vue`, `PlannerStudentPool.vue`, `GroupBoard.vue`, and `GroupCard.vue` now freeze the documented `480px` desktop lane floor plus `56px` assigned-row / `112px` empty-drop-zone floors. Focused proof was added in `PlannerGroupingWorkspacePane.smart-rules.spec.ts`, `GroupBoard.spec.ts`, and `GroupCard.spec.ts`.
- `PR-0227` browser proof now lives in `scripts/playwright_pr_0227_group_board_height_contract_check.py`. It follows the existing targeted Playwright proof pattern, reuses the shared planner/browser helpers, and writes screenshots to `.artifacts/pr-0227-group-board-height-check/` for both public and authenticated routes.
- The guest regression reported after grouping mutations is fixed in `frontend/apps/skriptoteket/src/views/apps/classroomPlannerGuestDraftPersistence.ts`. Grouping autosave now preserves `selected_template_local_id` instead of overwriting it with `null`, so overview-selected classrooms survive `Slumpa` / grouping edits and `Sittplatser` stays enabled.
- Fresh grouping drafts are now normalized to 4 default groups in both lanes: guest/browser-owned seeding in `classroomPlannerGuestDraftPersistence.ts` and authenticated/backend seeding in `src/skriptoteket/application/curated_apps/classroom_planner/handlers/workspace_builders.py`.
- Docs are updated locally: `docs/backlog/prs/pr-0226-st-29-11-shared-planner-shell-parity-and-grouping-viewport-height-stabilization.md` is now `done`, `docs/backlog/prs/pr-0227-st-29-11-exact-two-row-grouping-board-height-contract-at-desktop-baseline.md` now freezes the desktop `min-height` plus empty-state exactness split, and `PR-0228` plus its retained `REV-PR-0228` review are now closed on the corrected page/workspace-scroll model with the authenticated real-data live proof lane and focused guest/auth shell specs as the explicit parity boundary.
- The legacy docs follow-up is now explicitly closed: `EPIC-34` scopes the docs-as-code tightening lane, `ST-34-02` and `PR-0230` have finished the remaining duplicate review-id families (`REV-EPIC-08`, `REV-EPIC-14`, `REV-EPIC-23`), and the old patch-workflow brief is preserved as linked support material for `REV-PR-0031`.
- The retained review corpus now shares the canonical review section shape again, and the validator passes after the follow-up cleanup of `REV-PR-0031`, `REV-ST-23-06`, `REV-ST-14-35`, and the remaining pending review placeholders.

### Previous Verification

- `pdm run docs-validate` (pass after adding and approving `REV-EPIC-34`, and updating `EPIC-34`, `docs/index.md`, and `.codex/handoff.md`)
- `pdm run docs-validate` (pass after scaffolding `EPIC-34`, `ST-34-01`, `ST-34-02`, and `PR-0230`, and updating `docs/index.md` plus `.codex/handoff.md`)
- `pdm run docs-validate` (pass after reconciling `docs/reference/ref-review-workflow.md`, `docs/templates/template-review.md`, `.codex/rules/096-review-workflow.md`, `.codex/rules/000-rule-index.md`, and `.codex/handoff.md` around primary-target semantics and ADR handling)
- `pdm run docs-validate` (pass after migrating `REV-EPIC-08` / `REV-EPIC-14` / `REV-EPIC-23` family records to canonical target-based review docs, preserving the legacy patch-workflow brief as linked support material, and repairing the backlog/index crosslinks)
- `pdm run docs-validate` (pass after normalizing the retained review section shape, preserving the PR-0031 support brief, and cleaning the remaining placeholder-heavy review bodies)
- `pdm run fe-test src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` (pass; 5 files / 48 tests after restoring page-scroll ownership and the `480px` grouping + seating rails)
- `pdm run fe-test src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerView.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/App.spec.ts src/components/layout/AuthLayout.spec.ts` (pass; 11 files / 96 tests)
- `pdm run fe-type-check` (pass)
- `pdm run python -m scripts.playwright_pr_0227_group_board_height_contract_check --base-url http://127.0.0.1:5173` (pass; authenticated `SA24D` / `G20` proof on the corrected model, screenshots in `.artifacts/pr-0227-group-board-height-check/`)
- Live authenticated browser measurement against `http://127.0.0.1:5173/apps/classroom.group-seating-studio` using the real `SA24D` / `G20` workspace (pass on corrected local model):
  - `Grupper` at `1366x768`: `main.auth-main-content` is the page/workspace scroller (`scrollHeight=1730`, `clientHeight=711`), the board stays on that main scroll path (`grouping-board-lane height=1313.5`), and the left rail is capped to `480px` with internal list overflow (`grouping-student-pool-scroll-body 932 > 405`)
  - `Grupper` after scrolling `main.auth-main-content` to `420px`: toolbar settles into the working band (`toolbarTop=89`, `toolbarBottom=135`) and the grouping rail remains present just below it (`poolTop=151`)
  - `Sittplatser` at `1366x768`: `main.auth-main-content` is the page/workspace scroller (`scrollHeight=1094`, `clientHeight=711`), the seating rail is capped to `480px` with internal list overflow (`seating-student-pool-scroll-body 1254 > 405`), and the room canvas remains the main seating surface (`room-canvas-viewport height=557.98`)
- `pdm run fe-test src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerView.spec.ts` (pass; 8 files / 88 tests)
- `pdm run fe-test src/views/apps/useClassroomPlannerGuestOverviewShell.spec.ts` (pass; 10 tests after adding classroom-persistence + 4-group guest seed coverage)
- `pdm run fe-type-check` (pass)
- `pdm run fe-test src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts` (pass; 15 tests for the `PR-0227` board/card contract)
- `pdm run fe-test src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/GroupBoard.spec.ts src/views/apps/components/GroupCard.spec.ts` (pass; 5 files / 51 tests)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py` (pass; 20 tests, including authenticated grouping-draft seed count)
- `pdm run python -m scripts.playwright_pr_0227_group_board_height_contract_check --base-url http://127.0.0.1:5173` (pass; public + authenticated route proof, screenshots in `.artifacts/pr-0227-group-board-height-check/`, asserts empty 4-card board `480px`, row gap `12px`, card floor `234px`, post-assignment floor persistence, and populated-card growth without internal scrolling)
- `pdm run docs-validate` (pass after `PR-0227` status + implementation verification updates)
- `pdm run docs-validate` (pass after tightening `EPIC-SKRIPT-29`, `ST-29-03`, `ST-SKRIPT-29-11`, and `PR-0228` so CSS-owned geometry and the missing `PR-0228` proof path are explicit in docs)
- `pdm run docs-validate` (pass after reconciling `PR-0228`, `REV-EPIC-29`, `ST-SKRIPT-29-11`, and `EPIC-SKRIPT-29` to the corrected page/workspace-scroll model while keeping the slice open pending a guest/auth parity close-out decision)
- `pdm run docs-validate` (pass after adding `TASK-SKRIPT-29-11-02` for desktop-first toolbar breakpoint overflow escalation and undo/redo shortcut parity, and updating `ST-SKRIPT-29-11`, `docs/index.md`, and handoff)
- `pdm run docs-validate` (pass after adding `ADR-SKRIPT-0080`, creating `PR-0231` and `PR-0232`, trimming `PR-0223` to the shipped baseline, and updating `ST-32-06`, `EPIC-32`, `docs/index.md`, and `.codex/handoff.md`)
- `pdm run docs-validate` (pass after adding `REV-PR-0231`, linking it from `PR-0231` / `PR-0232`, and updating `docs/index.md` plus `.codex/handoff.md`)
- `pdm run docs-validate` (pass after addressing `REV-PR-0231` findings by tightening `PR-0231` and `PR-0232` around mandatory public Smart/export route families and explicit abuse-control requirements)
- `pdm run docs-validate` (pass after re-reviewing `REV-PR-0231`, approving the retained guest-boundary planning gate, and updating `.codex/handoff.md`)
- `pdm run fe-test -- --run src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts` (pass; 4 files / 10 tests for guest overview/shell parity plus the new public Smart composables)
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py` (pass; 7 tests for stateless public smart handlers and public helper routes)
- `pdm run fe-type-check` (pass)
- `pdm run docs-validate` (pass)
- `pdm run lint` (pass after adding the missing shared migration coverage registration for `d3a9f6b2c4e7` in `tests/integration/migration_schema_assertions.py`)
- Live public browser proof against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` with local backend on `http://127.0.0.1:8000`:
  - Created guest roster `SA24D`, opened `Grupper`, opened the guest Smart drawer, and confirmed the drawer exposes `Regler` plus classroom/seating controls but omits the account-only `Historik` section
  - Used `Öppna Regler` from the guest grouping Smart drawer and verified the shared `Regler` workspace rendered in the public lane
  - Enabled guest `Smart` in `Grupper`, clicked `Slumpa`, and confirmed a live `POST /api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run` request returned `200 OK`
  - Confirmed the applied guest workspace updated in place after the public Smart run (`Ej grupperade` dropped to `0`, each of the four students landed in a group, top status changed to `Sparad`)
- `pdm run docs-validate` (pass after adopting the target-based review-doc model, splitting the active `EPIC-SKRIPT-29` follow-up review gates into `REV-PR-*` docs, and retiring the old planning-doc lane)
- `pdm run docs-validate` (pass after the backlog close-out cleanup: `EPIC-34` -> `done`, `ST-09-04` -> `done`, `REV-EPIC-29` -> `approved`, `REV-ST-23-06` -> `approved`, `REV-SKRIPT-ST-08-27-CLOSEOUT` -> `changes_requested`, and older re-review/addendum docs normalized so status and verdict no longer disagree)
- `pdm run fe-test src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts` (pass; 4 files / 42 tests for the shared guest/auth shell and grouping/seating pane contract used to close `PR-0228`)
- `pdm run fe-type-check` (pass)
- `pdm run python -m scripts.playwright_pr_0227_group_board_height_contract_check --base-url http://127.0.0.1:5173` (pass; authenticated `SA24D` / `G20` retained live proof for the corrected `PR-0228` shell contract)
- `pdm run docs-validate` (pass after closing `PR-0228`, approving `REV-PR-0228`, and updating `ST-SKRIPT-29-11`, `EPIC-SKRIPT-29`, and `.codex/handoff.md`)
- `repomix --style xml --no-gitignore --output .codex/repomix_packages/repomix-pr-0229-toolbar-breakpoint-overflow-review.xml --include "AGENTS.md,.codex/rules/000-rule-index.md,.codex/rules/045-huleedu-design-system.md,.codex/rules/070-testing-standards.md,.codex/rules/075-browser-automation.md,.codex/handoff.md,docs/reference/ref-review-workflow.md,docs/backlog/reviews/review-epic-29-klassrumskartan-desktop-first-workspace-overhaul.md,docs/backlog/reviews/review-pr-0229-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md,docs/backlog/prs/pr-0225-st-29-11-desktop-first-planner-toolbar-priority-and-overflow-hardening.md,docs/backlog/prs/pr-0229-st-29-11-desktop-first-planner-toolbar-breakpoint-overflow-escalation-and-undo-redo-shortcut-parity.md,docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md,docs/backlog/stories/story-29-11-klassrumskartan-shared-site-and-app-dense-control-primitive-tightening.md,frontend/apps/skriptoteket/src/assets/main.css,frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceActionBar.spec.ts,frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerToolbarOverflowMenu.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerExportActionGroup.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts,frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue,frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts,frontend/apps/skriptoteket/src/components/ui/useDenseMenuSurface.ts"` (pass; 26 files, 66,084 tokens, output `.codex/repomix_packages/repomix-pr-0229-toolbar-breakpoint-overflow-review.xml`)
- `pdm run docs-validate` (pass after planning `PR-0228` and clarifying sticky student-pool ownership in `ST-29-03` / `ST-29-05`)
- `pdm run fe-test src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts` (pass; 4 files / 42 tests)
- `pdm run fe-type-check` (pass)
- `pdm run docs-validate` (pass after recording the retained `PR-0228` review outcome and real `SA24D` / `G20` verification evidence)

### Source: 2026-04-08 handoff compaction dump

Moved from `.codex/handoff.md` during handoff cleanup.

### Previous Status

- `PR-0234` is shipped. The assessed root cause was the public guest overview -> grouping seam dropping the selected classroom by opening grouping with `templateId = null`, plus stale pending template refs keeping `Sittplatser` visually enabled after live classroom context was gone. A small helper module now centralizes the live guest classroom-context rule, overview -> grouping preserves the selected classroom, and the guest shell disables `Sittplatser` from real live context rather than stale pending refs.
- `PR-0235` is shipped. The shared viewport helper keeps the framed-surface fit model across builder / seating / rules, fit-to-view is explicitly capped at `100%`, and the pure helper seam now has focused coverage so the repo no longer relies on stale pre-frame numbers in `useRoomViewportZoom.spec.ts`.
- `PR-0236` is shipped. The stale isolated roster-overview spec now passes `showActions` explicitly when asserting the visible action footer, also proves the hidden-footer case when actions are disabled, and keeps class-list import inside the create/edit workflow.
- `PR-0237` is now decided and documented as done:
  - `docs/mockups/st-32-07-public-landing-discoverability/designer-a.html` is the winning submission
  - the canonical blueprint artifact for follow-on work is the separate copy `docs/mockups/st-32-07-public-landing-discoverability/index.html`
  - do not refine or overwrite `designer-a.html`; any further iteration should branch from the copy, not the original submission
  - carry forward the review caveats that any baseline overlay is working scaffolding only and that minor monospace / uppercase micro-markers can be softened later without reopening the layout direction

### Previous Verification

- `pdm run fe-test -- --run src/views/apps/roomBuilderViewport.spec.ts src/views/apps/useRoomViewportZoom.spec.ts src/views/apps/components/RoomTemplateBuilderSurface.spec.ts src/views/apps/components/RoomCanvas.spec.ts src/views/apps/components/PlannerRulesMapCanvas.spec.ts` (pass; `PR-0235` framed viewport contract + 100% cap across helper/composable/shared consumers)
- `pdm run fe-test -- --run src/views/apps/components/PlannerRosterOverviewPanel.spec.ts src/views/apps/components/PlannerClassWorkspace.spec.ts src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts` (pass; `PR-0236` capability-gated roster overview spec realignment)
- `pdm run fe-type-check` (pass after the `PR-0235` helper/spec realignment)
- `pdm run fe-type-check` (pass after the `PR-0236` spec realignment)
- `pdm run fe-test` (pass; 149 files, 771 tests)
- Live local browser proof on `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass for `PR-0235`; public builder modal rendered `builder-zoom-percent = 100%` and `room-builder-scroll-frame[data-overflow-anchor] = center` for a fresh small-room state; Playwright Chrome session was explicitly closed after the check)
- `pdm run docs-validate` (pass after implementing `PR-0236`, updating remediation task statuses, and refreshing `.codex/handoff.md`)
- `pdm run docs-validate` (pass after scaffolding `ST-32-07` and `PR-0237` through `PR-0240`)
- `repomix --style xml --no-gitignore --output .codex/repomix_packages/repomix-pr-0228-workspace-contract-review.xml --include "AGENTS.md,.codex/rules/000-rule-index.md,.codex/rules/075-browser-automation.md,.codex/handoff.md,docs/reference/ref-review-workflow.md,docs/backlog/reviews/review-epic-29-klassrumskartan-desktop-first-workspace-overhaul.md,docs/backlog/reviews/review-pr-0228-planner-workspace-shell-breakpoint-and-overflow-contract.md,docs/backlog/prs/pr-0228-st-29-11-follow-up-desktop-student-pool-rail-stickiness-restoration.md,docs/backlog/stories/story-29-03-klassrumskartan-shared-desktop-workspace-composition-primitives.md,docs/backlog/stories/story-29-05-klassrumskartan-grouping-and-seating-desktop-workspace-overhaul.md,frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerView.vue,frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceModeSurface.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerStudentPool.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspaceToolbar.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspaceToolbar.vue,frontend/apps/skriptoteket/src/views/apps/components/PlannerTopPanel.vue,frontend/apps/skriptoteket/src/views/apps/components/GroupBoard.vue,frontend/apps/skriptoteket/src/views/apps/components/RoomCanvas.vue,frontend/apps/skriptoteket/src/views/apps/plannerWorkspaceLayout.ts,frontend/apps/skriptoteket/src/views/apps/components/PlannerGroupingWorkspacePane.smart-rules.spec.ts,frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts,frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts,frontend/apps/skriptoteket/src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts,scripts/playwright_pr_0227_group_board_height_contract_check.py"` (pass; 28 files, 72,943 tokens, output `.codex/repomix_packages/repomix-pr-0228-workspace-contract-review.xml`)
- `pdm run fe-test -- --run src/views/apps/classroomPlannerGuestDraftWorkspace.spec.ts` (pass; 1 test proving reused guest grouping drafts persist the newly selected classroom into the browser snapshot and next public Smart payload)
- `pdm run pytest tests/unit/web/test_public_apps_classroom_planner_smart.py` (pass; 4 tests including the oversized streamed-body `413` guard that never reaches the anonymous Smart handler)
- `pdm run pytest tests/unit/web/test_public_apps_classroom_planner_smart.py` (pass; 5 tests including a real-provider DI regression that proves smart routes honor `PUBLIC_HELPER_SMART_RUN_*` even when `PUBLIC_HELPER_RATE_LIMIT_*` is stricter)
- `pdm run fe-test -- --run src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts` (pass; 2 files / 4 tests, including rollback when guest snapshot persistence blocks after a public Smart result)
- `pdm run pytest tests/unit/web/test_public_apps_classroom_planner_imports.py tests/unit/infrastructure/security/test_public_helper_request_throttle.py` (pass; 12 tests covering the shared helper-throttle contract plus unchanged import-preview behavior under the new per-helper-family throttle API)
- `pdm run fe-type-check` (pass after the review-fix follow-up)
- `pdm run lint` (pass after the review-fix follow-up)
- Live browser render check against `http://127.0.0.1:5173/public/apps/classroom.group-seating-studio` (pass; public Klassrumskartan route returned `200 OK` and rendered the `Klassrumskartan` heading in the SPA after the guest draft/public Smart follow-up fixes)
- Live backend API check against `http://127.0.0.1:8000/api/v1/public/apps/classroom.group-seating-studio/grouping/smart-run` (pass; returned `200 applied` with `Smart gruppindelning klar med stöd från klassens sittschema.` after the helper-family-aware DI throttle fix)
- `pdm run docs-validate` (pass after returning `REV-ST-09-09` to `changes_requested`, restoring `ADR-SKRIPT-0081` / `ST-09-09` to proposed/ready, and removing the premature launcher close-out claims)
- `bash -n scripts/hemma_deploy_start.sh` (pass)
- `bash -n scripts/hemma_deploy_monitor.sh` (pass)
- `pdm run hemma-deploy --help` (pass; confirms the canonical detached-launch operator command is registered)
- `pdm run hemma-deploy-monitor --help` (pass; confirms the best-effort filtered monitor command is registered)
- `pdm run docs-validate` (pass after approving `REV-ST-09-09`, accepting `ADR-SKRIPT-0081`, moving `ST-09-09` to `in_progress`, updating the Hemma runbook, and wiring the new PDM commands)
- Live production proof on Hemma (pass on 2026-04-07 without a second deploy after the monitor tweak):
  - `pdm run hemma-deploy` handed off detached remote PID `1243606`
  - authoritative raw log: `/home/paunchygent/apps/skriptoteket/.artifacts/hemma-deploy-20260407-092323.log`
  - deployed commit: `94be5c23bbfb8294278cf21d3f679ee693277f73`
  - migrations applied successfully
  - seating-export smoke passed; deploy artifacts: `.artifacts/pr-0146-seat-export-cutover-20260407-092323/`
  - `scripts/hemma_deploy_monitor.sh` now replays the existing milestone/failure history from that authoritative raw log before following new output
- `bash -n scripts/hemma_deploy_start.sh` (pass after the final wording tweak)
- `bash -n scripts/hemma_deploy_monitor.sh` (pass after the replay-first monitor tweak; `shellcheck` unavailable locally)
- `pdm run docs-validate` (pass after closing `ST-09-09` as done and recording the live Hemma proof)
- `pdm run lint` (pass after the final Hemma deploy docs/launcher close-out)

### Previous How to Run

```bash
ARTIFACTS_ROOT=/tmp/skriptoteket/artifacts pdm run dev-local
pdm run fe-test -- --run src/views/apps/ClassroomPlannerGuestOverviewView.spec.ts src/views/apps/ClassroomPlannerGuestWorkspaceShell.spec.ts src/views/apps/usePublicSmartGroupingRun.spec.ts src/views/apps/usePublicSmartSeatingRun.spec.ts
pdm run pytest tests/unit/application/apps/classroom_planner/test_public_smart_run.py tests/unit/web/test_public_apps_classroom_planner_smart.py
pdm run fe-type-check
pdm run docs-validate
```

### Previous Known Issues / Risks

- The authenticated route still shows the pre-existing guest-upgrade import dialog with `Internal server error`; this did not block the planner verification because `Inte nu` closed it, but the upgrade/import path still needs its own debugging lane.
- `ClassroomPlannerView.spec.ts` still emits the pre-existing suppressed runtime warning from `resolveHomeRosterId(...)` during one centered-shell test even though the suite passes; it was not part of `PR-0226`.

### Previous Next Steps
