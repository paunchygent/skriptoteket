---
type: pr
id: PR-0308
title: "ST-29-11: Smart settings preference continuity and seating-influence default"
status: done
owners: "agents"
created: 2026-05-09
updated: 2026-05-09
stories:
  - "ST-29-11"
tags: ["frontend", "ux", "klassrumskartan", "smart"]
dependencies:
  - "PR-0305"
  - "PR-0306"
acceptance_criteria:
  - "Given an authenticated teacher has no saved Smart settings preference, when they create a new grouping draft and open `Avancerade inställningar`, then `Smart placering` is on, `Historik` is on, and `Tillämpa sittschema` is off."
  - "Given an authenticated teacher has no saved Smart settings preference, when they create a new seating draft and open `Avancerade inställningar`, then `Smart placering` is on and `Historik` is on."
  - "Given a public guest has no saved browser-owned Smart settings preference, when they create a new grouping draft and open `Avancerade inställningar`, then `Smart placering` is on, `Historik` remains omitted, and `Tillämpa sittschema` is off."
  - "Given a teacher explicitly changes `Smart placering`, `Historik`, or `Tillämpa sittschema`, when they create another draft, then the new draft seeds that setting from the last explicit preference instead of resetting every setting to the first-time default."
  - "Given a teacher clicks `Nytt utkast`, when the draft root changes, then the advanced Smart settings do not silently mutate away from the last explicit preference."
  - "Given `Tillämpa sittschema` is off, when Smart grouping runs with a selected classroom, then grouping does not use live seating continuity as a compactness/proximity input."
  - "Given `Tillämpa sittschema` is on and a classroom context is selected, when Smart grouping runs, then the existing live-seating continuity behavior remains available without changing solver weights."
---

## Problem

`PR-0306` intentionally aligned the remaining Smart settings as opt-out defaults. That made
`Smart placering`, authenticated `Historik`, and grouping-specific `Tillämpa sittschema` all default
on for fresh drafts.

That contract is too broad. `Tillämpa sittschema` is not a light helper; it can make `Slumpa` in
`Grupper` strongly prefer groups whose students already sit near one another. When a teacher creates
a new draft and this setting silently returns to on, the grouping result can look almost
deterministic or broken because the solver is doing exactly what the hidden default asked it to do.

The bug is therefore not the existence of the setting. The bug is that draft creation resets
advanced Smart intent, and the most powerful grouping-specific setting is enabled for first-time
users.

## Goal

Separate first-time defaults from remembered explicit choices:

- keep `Smart placering` on for first-time users
- keep authenticated `Historik` on for first-time users, but remember explicit opt-outs or opt-ins
- keep public guest `Historik` omitted
- make `Tillämpa sittschema` off for first-time grouping users
- remember the teacher's last explicit advanced Smart choices across `Nytt utkast`
- preserve the current Smart grouping solver behavior when the teacher explicitly enables seating
  influence

## Non-goals

- No solver scoring, weighting, compactness, history-window, or live-seating algorithm changes.
- No copy rewrite beyond wording required to make the default and preference model honest.
- No migration that rewrites existing historical drafts as if old implicit defaults were explicit
  teacher choices.
- No account-backed `Historik` affordance in public guest mode.
- No redesign of the toolbar, `Slumpa`, or `Avancerade inställningar` layout.

## Implementation plan

1. Introduce a small Smart settings preference source separate from the mutable draft root.
   - Authenticated drafts should seed from the teacher's last explicit preference when one exists.
   - Public guest drafts should seed from browser-owned preference state when one exists.
   - First-time fallback values should remain explicit and centralized.
2. Change first-time grouping fallback so `grouping_seating_distance_enabled` / `Tillämpa
   sittschema` is `false`.
3. Preserve first-time authenticated `use_history=true` and `smart_enabled=true`.
4. Persist preference only when the teacher explicitly changes the corresponding advanced setting,
   not merely because a draft was created or serialized.
5. Update new-draft creation, guest snapshot/draft builders, draft serialization helpers, and
   advanced-settings state helpers so `Nytt utkast` seeds from preference without overwriting saved
   draft-local values.
6. Keep Smart grouping's existing live-seating path gated by
   `grouping_seating_distance_enabled && selected classroom`.
7. Add focused regression coverage for first-time defaults, remembered explicit settings, and
   Smart grouping runs with seating influence off.

## Test plan

- `pdm run fe-gen-api-types`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_draft_lifecycle.py tests/unit/web/apps/classroom_planner/test_api.py tests/unit/application/identity/test_update_ai_settings_handler.py`
- `pdm run pytest tests/unit/application/identity/test_update_classroom_planner_settings_handler.py`
- `pdm run fe-test --run src/views/apps/useClassroomState.spec.ts src/views/apps/classroomPlannerSmartPreferences.spec.ts src/views/apps/classroomPlannerSmartRuleActions.spec.ts src/views/apps/classroomPlannerGuestDraftWorkspace.spec.ts`
- `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[b6c9f2a1d4e8]'`
- `pdm run lint`
- `pdm run typecheck`
- `pdm run fe-lint`
- `pdm run fe-type-check`
- `pdm run fe-build`
- `pdm run docs-validate`
- `pdm run handoff-validate`
- `pdm run alembic heads`
- `git diff --check`

## Implementation summary

Authenticated Smart settings are now profile-owned through nullable `UserProfile` fields and
`/api/v1/profile/classroom-planner-settings`, so explicit teacher choices persist across browsers
and seed new authenticated drafts. First-time authenticated drafts still start with `Smart
placering` and `Historik` on, but `Tillämpa sittschema` is off until explicitly enabled.

Public guest drafts keep the same first-time behavior for Smart and seating influence, with
`Historik` omitted/off, and remember explicit guest choices in browser storage only.

Authenticated preference writes are serialized through a dedicated frontend lane. New draft
lifecycle calls wait for that lane before posting to the backend, so `Nytt utkast` cannot read a
stale profile preference after an explicit Smart setting change.

## Rollback plan

Restore the `PR-0306` draft-default contract where `Tillämpa sittschema` defaults on with the other
Smart settings. Do not roll back unrelated Smart drawer copy, toolbar overflow placement, share/export
history provenance, or solver behavior.
