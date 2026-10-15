---
type: task
id: TASK-SKRIPT-08-36-02
title: Keep signed-in shell help and account actions reachable across breakpoints
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-10-15'
status: in_progress
closeout_review:
  record: inline
  status: not_started
task_kind: story
acceptance_criteria:
- Signed-in teachers can open Hjälp at 375, 900, 1024 and 1280+ px through the
  authenticated header or navigation drawer.
- Focus mode and logout remain reachable wherever the top-bar actions are hidden;
  focus mode can be exited and pending logout stays disabled.
- Focused Vitest coverage, SPA typecheck, lint and build, and docs validation pass.
story: ST-SKRIPT-08-36
backlog_document_profile: contract-derived
---

## Implementation Contract

Repair the signed-in shell mismatch from the failed 2026-10-15 staging walk.
Keep desktop actions in the existing top bar and expose Hjälp, focus mode and
logout in the drawer below the shell's route-specific desktop cutoff: 1280 px
for Klassrumskartan and 768 px for standard routes. Close the drawer on action
selection. Hjälp uses the shared panel and returns focus to the visible Meny
button when closed. Immersive routes retain Hjälp and logout through their sole
top bar at narrow widths. Use existing shell styling and design tokens.

Backend auth, tutorial content, shared design-system changes and staging
deployment are outside this task.

## Contract Inputs

- [ST-SKRIPT-08-36](../stories/st-skript-08-36-klassrumskartan-tutorial-clips-in-hjälp-with-a-first-use-dialog.md)
  requires replay from Hjälp at every width.
- The user's repair brief and FAILED staging-walk ruling on 2026-10-15.
- `AuthLayout.vue`, `AuthTopBar.vue`, `AuthSidebar.vue`, `HelpButton.vue` and
  `useHelp.ts` under `frontend/apps/skriptoteket/src/components/`.
- Closed retained decision ledger:
  `.orchestration/context/sessions/01a13f60-f5d1-7cee-9c93-2d226dad61de/evidence/planning/TASK-SKRIPT-08-36-02/plan.md`.

## Core Vertical And Performance

Core vertical: signed-in shell, Meny drawer, shared Hjälp panel, focus reversal
and logout event. One bounded junior unit implements shell controls and focused
component proof; the lead owns integration, validation and the branch commit.
CSS owns breakpoint geometry; no viewport listeners or requests are introduced.

## Validation

- `pdm run fe-test src/components/layout/AuthLayout.actions.spec.ts src/components/layout/AuthLayout.spec.ts src/components/layout/AuthSidebar.spec.ts`
  covers drawer help opening and focus restoration, focus-mode reversal, logout
  forwarding and pending-state suppression, and retained shell behavior.
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run fe-build`.
- `pdm run handoff-validate`, `pdm run docs-validate`, `git diff --check`.
- The parent owns the real signed-in staging click-through at 375, 900, 1024 and
  1280+ px after integration and deployment. Component tests do not establish
  rendered viewport success.

Implementation validation on 2026-10-15: the focused command passed 3 files /
16 tests; SPA typecheck, lint and build passed. Build reported a chunk-size
warning. Proof and exact changed files are retained in
`.orchestration/context/sessions/01a13f60-f5d1-7cee-9c93-2d226dad61de/evidence/implementation/TASK-SKRIPT-08-36-02/result.md`.
Independent review and the parent's live viewport walk remain pending.

## Stop Conditions

- Commit only on `fix/planner-hjalp-1024`, without attribution lines. Never push,
  change main, rebase, amend or deploy staging from this worktree.
- Independent review and the real browser walk remain parent-owned; leave the
  task in progress pending that evidence and closeout authority.
- Return any need for backend auth or shared design-system changes to the parent.

## Decided Contract Terms

| ID  | Decided contract term |
| --- | --------------------- |
| D01 | Signed-in Hjälp, focus mode and logout remain reachable through the header or drawer at every width; footer CSS follows the owning shell cutoff. |
| D02 | Reuse shared help, labels and tokens. Close the drawer on selection; help restores focus to Meny and focus mode remains reversible. |
| D03 | Add focused component proof and run SPA typecheck, lint, build and docs validation. The parent owns review, integration, deployment and live viewport walks. |
| D04 | Commit only on fix/planner-hjalp-1024 without attribution lines; never push, change main, rebase or amend. At most two fresh Pi DeepSeek Flash 4.1 juniors are authorized. |
