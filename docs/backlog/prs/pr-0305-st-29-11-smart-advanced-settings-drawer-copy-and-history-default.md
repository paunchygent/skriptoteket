---
type: pr
id: PR-0305
title: "ST-29-11: Smart advanced settings drawer copy and history default"
status: done
owners: "agents"
created: 2026-05-06
updated: 2026-05-06
stories:
  - "ST-29-11"
tags: ["frontend", "ux", "copy", "design-system", "klassrumskartan", "smart"]
dependencies:
  - "PR-0287"
  - "PR-0302"
acceptance_criteria:
  - "Given grouping or seating Smart settings are opened from the overflow settings group, when the drawer renders, then the title is exactly `Avancerade inställningar` and no eyebrow label such as `Smart` is shown above the title."
  - "Given the overflow menu shows class/classroom settings actions, when this slice ships, then the Smart settings affordance is moved into the same settings group as `Redigera klass` and `Redigera klassrum` and is labelled exactly `Avancerade inställningar`."
  - "Given the advanced settings drawer renders the master Smart control, when the label and copy are shown, then they are exactly `Smart placering` and `Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.`"
  - "Given an authenticated teacher creates or opens a grouping/seating draft without a saved history opt-out, when the advanced settings drawer renders, then `Historik` is on by default and remains an opt-out setting rather than an opt-in setting."
  - "Given the advanced settings drawer renders the history control, when the label and copy are shown, then they are exactly `Historik` and `Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.`"
  - "Given the advanced settings drawer renders the rules section, when the label, copy, and button are shown, then they are exactly `Regler`, `Lägg till och ändra regler för placeringar.`, and `Öppna Regler`."
  - "Given the teacher opens public guest grouping or seating Smart settings, when account-backed history is unavailable, then the `Historik` section remains omitted rather than exposing a disabled authenticated-only promise."
---

## Problem

`PR-0302` moved the split Smart toggle/settings control into overflow by default and made new
drafts Smart-enabled unless the teacher opts out. The remaining toolbar shape still treats Smart as
a special split affordance, while the settings panel copy is too abstract for teachers who want to
know what value the setting provides.

The old `Smart-inställningar` framing also leaves `Historik` feeling like an optional hidden feature
even though most teachers should benefit from export-backed anti-repeat placement by default.

## Goal

Lock the product-owner copy and settings structure before implementation:

- move the Smart settings entry into the overflow settings group beside class/classroom settings
- rename the settings surface to `Avancerade inställningar`
- put the Smart master toggle at the top of the drawer
- make `Historik` default on for authenticated history-capable drafts unless the teacher explicitly
  opts out
- preserve `Regler` as the dedicated rule-authoring workspace link

## Locked Copy

Drawer title:

```text
Avancerade inställningar
```

Smart section:

```text
Smart placering
Tar hänsyn till dina regler när du skapar en ny placering, till exempel fasta platser eller elever som inte bör sitta nära varandra.
```

History section:

```text
Historik
Försöker undvika att elever får samma plats eller samma bordsgrannar som tidigare. Stäng av om du vill börja utan historik.
```

Rules section:

```text
Regler
Lägg till och ändra regler för placeringar.
Öppna Regler
```

Overflow menu item:

```text
Avancerade inställningar
```

Forbidden copy in this slice:

- no eyebrow label above the drawer title
- no `Smart-inställningar` title
- no abstract explanation such as `valda underlag`, `variera placeringar över tid`, or similar
  internal-language framing

## Non-goals

- No Smart solver, scoring, rule-persistence, share/export, or payload-shape changes beyond the
  explicit `use_history` default.
- No inline rule creation inside the advanced settings drawer.
- No account-backed `Historik` affordance in public guest mode.
- No new drawer/dialog primitive unless the existing Smart settings drawer cannot meet the required
  modal-dialog semantics.

## Implementation plan

1. Move the Smart settings affordance from the Smart split control into the overflow settings group
   beside `Redigera klass` and `Redigera klassrum`.
2. Rename the drawer title and overflow item to the locked `Avancerade inställningar` copy.
3. Render the Smart master toggle as the first drawer section using the locked label and copy.
4. Change authenticated history defaults so `Historik` is on unless a saved opt-out exists.
5. Keep public guest history omitted because there is no account-backed export history.
6. Update focused component coverage for grouping and seating drawer copy, overflow menu placement,
   history default state, and guest history omission.

## Test plan

- `pdm run fe-test -- --run PlannerSmartSettingsDrawer PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow PlannerWorkspaceShell PlannerGroupingWorkspacePane.export PlannerSeatingWorkspacePane.export classroomPlannerSmartDefaults`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_draft_contracts.py -q`
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[3f6d8a2c4b91]' --override-ini addopts='' -q`
- `pdm run ruff check scripts/playwright_pr_0302_toolbar_overflow_parity.py scripts/_playwright_huleedu_auth.py tests/unit/scripts/test_playwright_script_surface.py`
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q`
- `pdm run alembic heads`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-type-check`
- `pdm run fe-lint`
- `pdm run fe-build`
- `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity --start-backend --start-vite`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `git diff --check`

## Implementation Summary

Closed on 2026-05-06:

- Grouping and seating overflow menus now expose `Avancerade inställningar` beside the existing
  edit settings actions instead of exposing the old Smart split affordance.
- Grouping and seating settings drawers are titled `Avancerade inställningar`, remove the `Smart`
  eyebrow, render `Smart placering` first with the locked explanatory copy, keep `Historik` as an
  authenticated opt-out setting, and preserve `Regler` as the dedicated rules-workspace link.
- `use_history` now defaults on across new domain drafts, API DTOs, and the database column default;
  migration `3f6d8a2c4b91` updates the server default while preserving explicit saved opt-outs.
- The retained toolbar parity proof now routes public Vite API calls to the same temporary backend
  as authenticated calls so public guest proof covers the new overflow settings item reliably.

## Verification

- `pdm run fe-test -- --run PlannerSmartSettingsDrawer PlannerGroupingWorkspaceToolbar.overflow PlannerSeatingWorkspaceToolbar.overflow PlannerWorkspaceShell PlannerGroupingWorkspacePane.export PlannerSeatingWorkspacePane.export classroomPlannerSmartDefaults` passed.
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_draft_contracts.py -q` passed.
- `pdm run pytest 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[3f6d8a2c4b91]' --override-ini addopts='' -q` passed.
- `pdm run alembic heads` reported `3f6d8a2c4b91 (head)`.
- `pdm run lint`, `pdm run typecheck`, `pdm run fe-type-check`, `pdm run fe-lint`, and
  `pdm run fe-build` passed; `fe-build` retains the existing large chunk-size warnings.
- `pdm run ruff check scripts/playwright_pr_0302_toolbar_overflow_parity.py scripts/_playwright_huleedu_auth.py tests/unit/scripts/test_playwright_script_surface.py` passed.
- `pdm run pytest tests/unit/scripts/test_playwright_script_surface.py -q` passed.
- `pdm run db-upgrade` applied local migration `0d9c5e8a2f31 -> 3f6d8a2c4b91` before live proof.
- `pdm run python -m scripts.playwright_pr_0302_toolbar_overflow_parity --start-backend --start-vite`
  passed across authenticated and public guest grouping/seating toolbar roundtrips with screenshots
  under `.artifacts/playwright-pr-0302-toolbar-overflow-parity/`.

## Rollback plan

Restore the prior Smart settings title, overflow split placement, and history default behavior. The
rollback is frontend-only and must not change stored rules, saved drafts, share/export artifacts, or
Smart solver contracts.
