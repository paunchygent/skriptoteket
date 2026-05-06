---
type: pr
id: PR-0306
title: "ST-29-11: Share priority and Smart settings opt-out parity"
status: done
owners: "agents"
created: 2026-05-06
updated: 2026-05-06
stories:
  - "ST-29-11"
tags: ["frontend", "ux", "copy", "design-system", "klassrumskartan", "smart"]
dependencies:
  - "PR-0286"
  - "PR-0302"
  - "PR-0305"
acceptance_criteria:
  - "Given grouping toolbar space is constrained, when lower-priority controls move into overflow, then the inline `Dela` affordance stays visible before the class selector wins inline space."
  - "Given seating toolbar space is constrained, when lower-priority controls move into overflow, then the inline `Dela` affordance stays visible before the classroom selector wins inline space."
  - "Given a first-time grouping user opens `Avancerade inställningar`, when no explicit opt-out exists, then `Smart placering`, authenticated `Historik`, and `Tillämpa sittschema` are on by default."
  - "Given a first-time seating user opens `Avancerade inställningar`, when no explicit opt-out exists, then `Smart placering` and authenticated `Historik` are on by default."
  - "Given a public guest opens advanced settings, when account-backed history is unavailable, then `Historik` remains omitted while the available Smart settings still default on until explicitly turned off."
  - "Given grouping advanced settings explains classroom selection, when the copy renders, then it is exactly `Välj vilket klassrum gruppindelningen hör till. Det avgör vilket sittschema Smart kan använda när Tillämpa sittschema är på.`"
  - "Given grouping advanced settings has no selected classroom, when the `Tillämpa sittschema` helper renders, then it is exactly `Välj först ett klassrum så Smart vet vilket sittschema som kan användas.`"
  - "Given grouping advanced settings has a selected classroom, when the `Tillämpa sittschema` helper renders, then it is exactly `Försöker lägga elever som redan sitter nära varandra i samma grupp. Det kan göra gruppstarten lugnare när eleverna ska arbeta från sina platser.`"
---

## Problem

`PR-0305` moved Smart tuning into `Avancerade inställningar`, but the remaining
grouping-specific seating influence setting still defaults off and the classroom helper copy is
too abstract. The responsive toolbar also needs an explicit regression guard that `Dela` remains
more important than the class/classroom selector when the toolbar starts moving controls into
overflow.

## Locked Copy

Grouping classroom selector:

```text
Välj vilket klassrum gruppindelningen hör till. Det avgör vilket sittschema Smart kan använda när Tillämpa sittschema är på.
```

Grouping seating influence, no classroom selected:

```text
Välj först ett klassrum så Smart vet vilket sittschema som kan användas.
```

Grouping seating influence, classroom selected:

```text
Försöker lägga elever som redan sitter nära varandra i samma grupp. Det kan göra gruppstarten lugnare när eleverna ska arbeta från sina platser.
```

## Behavioral Distinction

- `Klassrum` selects the room context for the grouping draft. It decides which classroom and
  sitting chart Smart can inspect if seating influence is enabled.
- `Tillämpa sittschema` is the opt-out switch for that influence. When it is on and a classroom is
  selected, Smart grouping may use current seat proximity from that classroom to prefer groups
  whose students already sit near each other. When it is off, Smart grouping still uses enabled
  Smart rules and history, but not current seat proximity.

## Non-goals

- No change to the Smart solver scoring weights or history semantics.
- No public guest account-backed `Historik` setting.
- No replacement of the shared toolbar overflow primitive.

## Test plan

- `pdm run fe-test -- --run PlannerSmartSettingsDrawer PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow classroomPlannerSmartDefaults classroomPlannerStateSupport classroomPlannerSmartRuleActions classroomPlannerGuestDraftWorkspace classroomPlannerGuestSnapshotMapping`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_draft_contracts.py -q`
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[8a6d4c2f1b09]' --override-ini addopts='' -q`
- `pdm run alembic heads`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

Closed on 2026-05-06:

- Grouping and seating toolbar overflow specs now explicitly prove that inline `Dela` remains
  visible while the class/classroom selectors and reset controls move into overflow.
- Follow-up correction: `Dela` is now the `distribution` overflow contribution in both grouping
  and seating, ordered after `context` and `reset`; the phone CSS no longer hides the toolbar
  distribution affordance outside the shared overflow ladder.
- `Smart placering`, authenticated `Historik`, and grouping `Tillämpa sittschema` now share the
  same opt-out default model. Public guest workspaces keep account-backed `Historik` omitted while
  defaulting the available Smart settings on.
- Authenticated draft defaults now align at the domain, API DTO, ORM, and database-server-default
  layers through migration `8a6d4c2f1b09`.
- The grouping advanced-settings classroom and seating-influence helper copy now uses the locked
  teacher-facing Swedish copy from this task.

## Verification

- `pdm run fe-test -- --run PlannerSmartSettingsDrawer PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow classroomPlannerSmartDefaults classroomPlannerSmartRuleActions classroomPlannerGuestDraftWorkspace classroomPlannerGuestSnapshotMapping` passed.
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_draft_contracts.py -q` passed.
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[8a6d4c2f1b09]' --override-ini addopts='' -q` passed.
- `pdm run alembic heads` reported `8a6d4c2f1b09 (head)`.
- `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run lint`, `pdm run typecheck`, `pdm run docs-validate`, and `git diff --check` passed.
- `pdm run db-upgrade` applied local migration `3f6d8a2c4b91 -> 8a6d4c2f1b09`; `pdm run dev-stack db-upgrade` completed, `pdm run dev-stack restart web` restarted the running API container, and `curl -fsS http://127.0.0.1:8000/healthz` plus `curl -fsS http://127.0.0.1:8080/healthz` passed.
- `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity --start-backend --start-vite` passed authenticated and public guest grouping/seating toolbar roundtrips with screenshots under `.artifacts/playwright-pr-0302-toolbar-overflow-parity/`.
- Follow-up correction verification passed: `pdm run fe-test -- --run PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow`, `pdm run fe-type-check`, `pdm run fe-lint`, `pdm run ruff check scripts/playwright_pr_0302_toolbar_overflow_parity.py tests/unit/scripts/test_playwright_script_surface.py`, `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`, and `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity --start-backend --start-vite`.
