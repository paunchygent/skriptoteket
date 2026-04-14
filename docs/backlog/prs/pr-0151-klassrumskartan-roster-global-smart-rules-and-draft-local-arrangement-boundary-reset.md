---
type: pr
id: PR-0151
title: "Klassrumskartan: roster-global smart rules and draft-local arrangement boundary reset"
status: done
owners: "agents"
created: 2026-03-27
updated: 2026-03-27
stories:
  - "ST-27-01"
tags: ["backend", "frontend-contract", "api", "persistence", "migrations", "klassrumskartan", "smart-assignment"]
dependencies:
  - "ADR-0074"
  - "EPIC-27"
  - "PR-0147"
acceptance_criteria:
  - "Given the teacher authors `Keep apart`, `Keep near`, or `Närmare läraren` for one class, when they later open another seating or grouping draft for that same class, then those same smart rules are still present because they are owned by the roster rather than one draft."
  - "Given the planner stores draft-local workspace state, when the backend persists current seating/group arrangements, draft smart toggles, or undo/redo history, then those draft mechanics remain draft-owned and do not duplicate the roster-global smart rules."
  - "Given the repo has no real users yet, when draft-owned smart-rule persistence is replaced, then the old draft-scoped rule tables, API fields, and store serialization paths are removed without compatibility shims."
  - "Given the planner loads or saves smart rules after this slice, when the API/domain/frontend interact, then roster-scoped rule contracts are used instead of draft PATCH/read contracts for those rules."
  - "Given the current local `PR-0149` seating smart-rule UI exists, when this slice lands, then that UI is retargeted to the roster-scoped smart-rule contract and no longer depends on draft autosave/PATCH or on `draft.smart_enabled` for authoring enablement."
  - "Given two tabs or drafts edit roster-global smart rules for the same class, when one save becomes stale, then the roster smart-rule write is rejected with an explicit conflict instead of silently overwriting the newer rules."
  - "Given draft-local arrangement edits and roster-global smart-rule edits can be dirty at the same time, when one persistence lane fails, then the other lane keeps its pending state and remains retryable instead of being silently cleared."
  - "Given the SPA loads a different draft or roster, when roster smart rules have not loaded yet or the follow-up smart-rule request fails, then the UI never renders the previous roster's smart rules against the new workspace."
  - "Given live planner verification can be blocked by unrelated local runtime failures, when this PR is reviewed, then the smart-rule ownership reset is verified by targeted backend/frontend suites plus a fresh planner smoke on `http://127.0.0.1:5173` after the active dev lane is schema-aligned."
---

## Problem

The current smart-assignment implementation and several docs still blur together three different
ownership lanes:

- class-global teacher intentions about students in one class
- draft-local arrangement state and draft controls
- export-backed history checkpoints

That blur leads to the wrong persistence model. It makes `Keep apart`, `Keep near`, and
`Närmare läraren` look like per-draft metadata even though the product decision is now clear: they
must stay global to the class list / roster across drafts.

## Goal

Reset the ownership boundary so smart rules become roster-global, while draft-local arrangement
state, draft toggles, and export-backed checkpoints remain separate concerns.

This slice also absorbs the current local `PR-0149` UI retargeting work so that the visual seating
authoring flow survives, but on the correct ownership boundary.

## Post-landing note

`PR-0151` is the ownership-boundary reset, not the final frontend session-shape cut-over.
`ST-27-06` / `PR-0152` now track the remaining planner remediation for explicit session
controller + lane-owned transition semantics, including removal of the shared frontend
flush/status/timer contract before `ST-27-03` and `ST-27-04`.

## Non-goals

- Implementing checkpoint registry/dedupe; that remains `PR-0150`.
- Delivering backend smart solver behavior.
- Adding new major teacher-facing UI beyond retargeting existing smart-rule authoring to the new
  boundary.
- Preserving backwards-compatible aliases for draft-owned smart-rule fields.
- Implementing checkpoint registry/dedupe side effects; that remains `PR-0150`.
- Deleting the remaining shared frontend planner session orchestration; that follow-up is
  `ST-27-06` / `PR-0152`.

## Implementation plan

1. Lock the corrected ownership model in tests first.
   - Add backend API tests that prove:
     - smart rules load per roster, not per draft
     - draft PATCH no longer accepts `seating_preferences` or `relationship_rules`
     - roster-scoped smart-rule endpoints accept and return those rules
   - Add repository/application tests that prove:
     - draft save/history no longer owns or snapshots smart rules
     - two drafts for the same roster see the same rule set
   - Add frontend tests that prove:
     - smart-rule authoring no longer depends on draft autosave
     - `Smart` off does not disable smart-rule editing

2. Split the domain boundary.
   - Introduce a roster-global smart-rule aggregate/value shape such as `RosterSmartRules`.
   - Remove smart-rule ownership from draft workspace models while keeping:
     - current seating/group arrangements
     - draft lifecycle/history
     - draft-level `Smart` / `Use history` controls
   - Keep any composition layer explicit when one UI response needs both draft-local and
     roster-global data.

3. Reset the application and API boundary.
   - Add roster-scoped smart-rule handlers and routes.
   - Remove smart-rule mutation from draft PATCH flows.
   - Allow draft/workspace GET composition to hydrate roster-global rules for convenience if
     helpful, but keep persistence paths separate.

4. Reset persistence.
   - Replace draft-owned smart-rule tables with roster-owned tables keyed to the class list /
     roster.
   - Keep draft tables focused on arrangement state, smart toggles, and draft history only.
   - Remove smart-rule snapshotting from bounded draft undo/redo history.

5. Retarget the current local `PR-0149` frontend work onto the new boundary.
   - Update the store/types so smart rules load/save through the roster-scoped contract.
   - Remove smart rules from draft autosave serialization.
   - Remove `draft.smart_enabled` as an authoring gate.
   - Keep the existing visual interaction model:
     - one active tool
     - unary `Närmare läraren`
     - multi-select `Håll isär` / `Håll nära`
     - non-overlap blocking
     - visible summary surface

6. Remediate the 2026-03-27 implementation review findings before landing.
   - Add optimistic concurrency for roster-global smart rules:
     - introduce a roster smart-rule revision/version contract at domain, repository, API, and frontend-store boundaries
     - require writes to supply `expected_revision` (or equivalent) and return `409` on stale saves
     - keep this concurrency boundary owned by the roster smart-rule aggregate rather than piggybacking on draft revisions
   - Split autosave lane failure handling so draft-local and roster-global writes cannot clear each other:
     - track pending draft changes and pending smart-rule changes independently through save success/failure
     - preserve retryability for the unaffected lane when the other lane errors
     - add store-level tests for mixed dirty state, partial failure, retry, and conflict handling
   - Make workspace hydration consistent across roster switches:
     - clear roster-global smart-rule state before applying a different workspace, or load workspace + smart rules atomically before mutating the visible store
     - add a failure-path test where the second smart-rule GET fails and confirm stale rules do not remain visible
     - keep the final contract explicit about which payload owns workspace state versus roster-global smart rules
   - Fix the false-conflict save path for roster smart-rule revision `0`:
     - treat revision `0` as a normal compare-and-swap state when a roster smart-rule root row already exists instead of assuming every `expected_revision == 0` write must create the row
     - ensure deletes/edits against repaired or backfilled root rows can advance from revision `0` to `1` without returning `409`
     - add repository/application/frontend regression coverage for the exact case `Expected 0, got 0` so only real stale writes surface as conflicts
   - Invalidate stale async planner work on clear/exit:
     - ensure `clearWorkspace()` invalidates in-flight workspace loads so a late response cannot reopen a cleared draft
     - ensure exit-without-waiting cannot let late autosave responses repopulate cleared state after Klassrumskartan leaves the workspace
     - add frontend regressions for both late-load and late-autosave-after-clear flows
   - Keep the final verification gate honest about unrelated planner/runtime failures:
     - if the host smoke fails outside the roster-smart-rule path, capture the blocking endpoint/stack trace and do not mark the smoke as passed
     - distinguish smart-rule regressions from pre-existing or adjacent planner/export runtime failures
     - only close the live-proof gate after rerunning the planner smoke against a host stack that is schema-aligned and free from unrelated 500s

## Files expected to change

- Backend/domain:
  - `src/skriptoteket/domain/curated_apps/classroom_planner/models.py`
  - `src/skriptoteket/protocols/classroom_planner.py`
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/drafts.py`
  - `src/skriptoteket/application/curated_apps/classroom_planner/handlers/planner_context.py`
  - `src/skriptoteket/web/api/v1/apps_classroom_planner.py`
  - `src/skriptoteket/web/app.py`
  - `src/skriptoteket/web/startup_checks.py`
  - `src/skriptoteket/infrastructure/repositories/classroom_planner.py`
  - `src/skriptoteket/infrastructure/db/models/classroom_planner_plan_draft.py`
  - `src/skriptoteket/infrastructure/db/models/classroom_planner_roster.py`
  - `src/skriptoteket/infrastructure/db/models/__init__.py`
- Frontend:
  - `frontend/apps/skriptoteket/src/views/apps/classroomPlannerTypes.ts`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.ts`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingSmartRuleSurface.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.vue`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.vue`
- Tests/migrations:
  - `tests/unit/application/apps/classroom_planner/test_grouping_exports.py`
  - `tests/unit/application/apps/classroom_planner/test_seating_exports.py`
  - `tests/unit/web/apps/classroom_planner/test_api.py`
  - `tests/unit/application/apps/classroom_planner/`
  - `tests/unit/infrastructure/repositories/`
  - `tests/unit/web/test_startup_checks.py`
  - `tests/integration/migration_schema_assertions.py`
  - `frontend/apps/skriptoteket/src/views/apps/useClassroomState.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
  - `frontend/apps/skriptoteket/src/views/apps/components/PlannerWorkspaceShell.spec.ts`
  - `migrations/versions/`
  - `pyproject.toml`
  - `.agents/rules/054-alembic-migrations.md`

## PR-sized execution checklist

- [x] Add/update backend API tests for roster-scoped rule load/save and draft PATCH rejection
- [x] Add/update application/repository tests proving draft history no longer owns smart rules
- [x] Add/update frontend tests proving draft autosave no longer carries rules and `Smart` off does not block authoring
- [x] Split domain models between roster-global smart rules and draft-local workspace state
- [x] Add roster-scoped API/handler boundary for smart rules
- [x] Add roster-owned ORM/repository + Alembic revision
- [x] Remove draft-owned smart-rule serialization from draft load/save paths
- [x] Retarget the current local `PR-0149` store/components to the roster-global contract
- [x] Re-run the existing seating smart-rule UI tests after retargeting
- [x] Re-run live planner verification on `http://127.0.0.1:5173` after the schema-aligned dev lane is recovered, then record the result in `.agents/handoff.md`
- [x] Add roster smart-rule optimistic concurrency and stale-write conflict handling
- [x] Keep draft autosave and smart-rule autosave retry state independent on partial failure
- [x] Prevent stale smart rules from rendering during workspace switches or second-request failure
- [x] Re-run targeted backend/frontend verification for the remediation slice and update `.agents/handoff.md`
- [x] Add fail-fast startup checking for stale host DB revisions
- [x] Add a forward repair migration for impossible roster smart-rule drift states
- [x] Move planner export hydration onto one explicit owner-scoped workspace loader
- [x] Make Docker dev-start/recreate paths auto-run the in-container `pdm run db-upgrade`
- [x] Fix the false `Expected 0, got 0` smart-rule conflict path for repaired/backfilled revision-0 root rows
- [x] Invalidate stale in-flight workspace loads and autosaves after clear/exit so late responses cannot repopulate cleared planner state
- [x] Invalidate or reject stale autosave responses when the teacher switches from one draft/roster workspace to another
- [x] Preserve same-lane dirty state when new draft or smart-rule edits happen during an in-flight autosave
- [x] Normalize or reject `near_teacher: false` seating-preference entries so ghost near-teacher markers cannot render

## Test plan

- `pdm run pytest tests/unit/web/apps/classroom_planner/test_api.py -q`
- `pdm run pytest tests/unit/application/apps/classroom_planner/ -q`
- `pdm run pytest tests/unit/infrastructure/repositories/ -q`
- `pdm run pytest tests/integration/migration_schema_assertions.py -q`
- `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[<new_revision_id>]' -q`
- `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.export.spec.ts src/views/apps/components/RoomCanvas.spec.ts`
- `pdm run fe-test -- --run <updated seating smart-rule spec files>`
- `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rules.py tests/unit/web/apps/classroom_planner/test_smart_rules_api.py tests/unit/infrastructure/repositories/test_classroom_planner_smart_rules.py -q`
- `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- `pdm run fe-type-check`
- `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
- `pdm run docs-validate`

## 2026-03-27 Ruthless Review Findings

1. Stale autosave responses can still apply after a workspace switch.
   - Finding:
     - The current async invalidation only runs on `cancelPendingSave()` / `clearWorkspace()`.
     - If draft A has an in-flight save and the teacher opens draft B, the late draft-A response can still pass the save-generation guard and reapply draft-A workspace or roster-smart-rule state into the draft-B session.
   - Suggested solution:
     - Invalidate the active save generation on every workspace switch/load/activate path, not just on clear/exit.
     - Bind draft and smart-rule save responses to the draft/roster identity they were issued for and ignore mismatches even if the generation still matches.
   - Required proof:
     - Add a store regression where draft A starts an autosave, draft B loads before the response resolves, and the late draft-A response must not change the visible draft, roster, or smart rules.

2. Same-lane edits can be lost when a save response lands after newer local edits.
   - Finding:
     - The store currently reapplies returned workspace/smart-rule payloads and clears the corresponding dirty flag on save success.
     - If the teacher makes more draft edits or more smart-rule edits while that lane is already saving, the first success response can wipe the newer local edits and leave the queued rerun with nothing dirty to persist.
   - Suggested solution:
     - Track per-lane mutation versions or request snapshots for draft autosave and smart-rule autosave separately.
     - Only clear a lane's dirty flag when no newer edits happened after that request started, and do not let a stale success payload overwrite newer local state.
   - Required proof:
     - Add one regression for draft edits made during an in-flight draft save and one for smart-rule edits made during an in-flight smart-rule save; each should prove the lane stays dirty or sends a second patch after the first response lands.

3. False-valued `near_teacher` entries can create ghost rule rendering.
   - Finding:
     - The backend currently accepts and persists `seating_preferences` entries where `near_teacher` is `false`.
     - The frontend summary/selection logic treats the presence of an entry as an active near-teacher rule, which can render ghost `Närmare läraren` markers from malformed or repaired data.
   - Suggested solution:
     - Normalize false-valued entries away or reject them at the handler boundary before persistence.
     - Make frontend checks require `near_teacher === true` instead of treating any matching entry as active.
   - Required proof:
     - Add application/API coverage that false-valued entries are stripped or rejected, plus a frontend/store regression proving they do not render as active rules.

## Review Remediation Subtasks

1. Add roster smart-rule revision ownership.
   - Introduce a `RosterSmartRules` revision/value contract and persist it alongside the roster-owned rules.
   - Reject stale smart-rule PATCH requests with `409` and a clear API error payload.
   - Update the SPA store to include the expected revision on every smart-rule save and reload on conflict.
   - Correct the repository CAS logic so `expected_revision == 0` can update an already-existing root row at revision `0` instead of raising a false conflict.
   - Cover the specific teacher flow where a repaired/backfilled roster loads old rules at revision `0`, the teacher deletes one rule, and the save must succeed as revision `1`.

2. Decouple autosave lane retries.
   - Refactor the store so draft-state saves and smart-rule saves have separate success/failure bookkeeping.
   - Ensure a smart-rule failure does not clear pending draft edits, and a draft failure does not clear pending smart-rule edits.
   - Add regression tests for partial failure, retry after failure, and mixed-lane flush-before-history actions.

3. Make workspace hydration atomic or fail-safe.
   - Clear roster smart-rule state as soon as a different workspace begins loading, or stage both responses and commit them together.
   - Add a failure-path test for the second smart-rule request and a switch-roster test proving the previous roster's rules never remain visible.
   - Keep the UI disabled/busy semantics aligned with the chosen loading strategy so teachers cannot interact with mismatched state.
   - Invalidate in-flight workspace loads when `clearWorkspace()` runs so a stale response cannot reopen a draft after exit or workspace teardown.
   - Keep late autosave responses from applying after exit-without-waiting has cleared planner state.

4. Guard autosave responses across workspace switches.
   - Invalidate the active save generation whenever the teacher loads or activates a different workspace, not only on clear/exit.
   - Carry the draft/roster identity with each in-flight save request and ignore late responses that target an older workspace.
   - Add a regression proving a late draft-A autosave cannot overwrite a newer draft-B session or re-show draft-A smart rules.

5. Preserve same-lane edits that happen during an in-flight autosave.
   - Track per-lane mutation versions or request snapshots separately for draft autosave and smart-rule autosave.
   - Only clear `hasPendingDraftAutosave` or `hasPendingSmartRuleAutosave` when the response still matches the latest local edit generation for that lane.
   - Add regressions for both lanes showing that edits made during an in-flight save either trigger a second patch or remain pending after the first response lands.

6. Normalize false-valued near-teacher rules across backend and frontend.
   - Strip or reject `near_teacher: false` seating-preference rows at the smart-rule handler boundary so persisted data stays canonical.
   - Update store/component checks so only `near_teacher === true` counts as an active near-teacher rule.
   - Add backend and frontend regressions proving false-valued entries do not survive persistence and do not render as active markers.

## Robust Solution Notes

The review-remediation solution for the smart-rule ownership reset is now:

1. Roster-global smart rules own their own revision and concurrency boundary.
   - Persist the roster rule set through a dedicated aggregate root with its own revision.
   - Require smart-rule writes to include `expected_revision`.
   - Return `409` on stale writes instead of silently overwriting newer rules.
   - Keep this versioning separate from draft revisions so draft-local arrangement saves and roster-global rule saves cannot corrupt each other.
   - Repository compare-and-swap logic must treat revision `0` as a real persisted state, not as shorthand for “row absent,” because repair/backfill migrations can legitimately create a root row at revision `0`.
   - The write path should therefore support both cases:
     - create-on-first-write when the root row is absent and `expected_revision == 0`
     - update-from-zero when the root row exists and its stored revision is also `0`
   - Only a stored revision different from the caller's expected revision should return `409`.

2. Draft autosave and smart-rule autosave are separate save lanes.
   - Track dirty/in-flight/error state independently for draft-local workspace state and roster-global smart rules.
   - Allow one lane to fail without clearing the other lane's pending retry state.
   - Preserve conflict feedback when one lane reports `409` and the other lane later reports a generic save error.

3. Workspace hydration is fail-safe across roster switches.
   - Clear roster smart-rule state before showing a newly loaded workspace, or stage both responses before committing visible state.
   - Ignore stale follow-up responses from an older workspace request.
   - Disable smart-rule authoring until roster rules are hydrated for the current workspace.
   - `clearWorkspace()` must also invalidate any in-flight load/save work so exit flows cannot repopulate state after teardown.

4. Host planner smoke remains a separate verification gate, not proof of the smart-rule remediation by itself.
   - If the host planner route fails in a different subsystem, capture that blocker explicitly instead of treating it as a smart-rule regression.
   - Current known examples from local verification were a transient missing grouping-export table on the host DB, a grouping-export handler that previously assumed `DraftWorkspace.template`, and a Docker DB stamped at head while still carrying the older partial roster-smart-rule FK shape.
   - The durable fixes for those classes of failures are:
     - fail fast on startup or dev boot when the DB revision is behind required migrations or when current-head schema shape is impossible
     - keep export handlers dependent on an explicit hydrated export workspace, not partially hydrated draft-local models

5. Applied migrations are immutable and Docker dev boot must self-heal.
   - Treat any migration already run against a persistent dev/staging DB as immutable; follow-up fixes belong in a new forward repair migration, not by editing the old revision in place.
   - The durable recovery for the observed Docker drift state is the repair-forward Alembic revision `7d4c1a2b9e6f`.
   - Docker dev startup/recreate/reset paths now run the in-container `pdm run db-upgrade` step so long-lived containers do not keep serving against stale schemas after migration files change.

6. Autosave correctness needs both generation invalidation and per-lane edit versioning.
   - Generation invalidation alone is not enough because it protects clear/exit flows but not workspace switches or newer edits in the same lane.
   - The durable fix is a two-part contract:
     - invalidate or reject responses whose workspace identity no longer matches the active draft/roster
     - track draft-lane and smart-rule-lane edit versions so a stale success response cannot clear newer pending edits

7. Near-teacher rules should persist in canonical true-only form.
   - `near_teacher: false` should not be stored as a meaningful rule state because the UI and future solver logic interpret the existence of the preference as teacher intent.
   - The durable boundary is therefore:
     - reject or strip false-valued entries before persistence
     - treat only explicit `true` values as active in frontend selectors, summaries, and render markers

## Verification Evidence

- Backend review-remediation suite:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_smart_rules.py tests/unit/web/apps/classroom_planner/test_smart_rules_api.py tests/unit/infrastructure/repositories/test_classroom_planner_smart_rules.py -q`
  - includes a regression that simulates a repaired/backfilled root row at revision `0` and proves the first edit advances it to revision `1` instead of returning `409`
- Export/runtime hardening suite:
  - `pdm run pytest tests/unit/application/apps/classroom_planner/test_grouping_exports.py tests/unit/application/apps/classroom_planner/test_seating_exports.py tests/unit/web/test_startup_checks.py -q`
- Smart-rule repair migration coverage:
  - `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[7d4c1a2b9e6f]' -q`
- Frontend review-remediation suite:
  - `pdm run fe-test -- --run src/views/apps/useClassroomState.spec.ts src/views/apps/components/PlannerWorkspaceShell.spec.ts src/views/apps/components/PlannerSeatingWorkspacePane.smart-rules.spec.ts`
- Type safety:
  - `pdm run fe-type-check`
  - `pdm run typecheck`
- Migration coverage:
  - `pdm run pytest -m docker 'tests/integration/test_migration_revision_coverage_idempotent.py::test_uncovered_migration_revision_is_idempotent[5f2c7d1a9b8e]' -q`
- Live schema repair:
  - `pdm run db-upgrade`
  - `pdm run dev-stack db-upgrade`
- Docs:
  - `pdm run docs-validate`
- Live planner smoke on `5173`:
  - `pdm run python -m scripts.playwright_classroom_planner_smoke --base-url http://127.0.0.1:5173`
  - artifact: `.artifacts/classroom-planner-smoke/classroom-planner-smoke.png`
- Live backend proof after hardening:
  - `healthz` returned `200` on `http://127.0.0.1:8000/healthz`
  - an authenticated GET to `/api/v1/apps/classroom.group-seating-studio/drafts/grouping/<draft_id>/exports/jobs/recover` returned `200` with `null` for the latest grouping draft instead of a `500`
  - the live Docker DB now reports Alembic revision `7d4c1a2b9e6f`, the root table `classroom_planner_roster_smart_rule_sets` exists, and both roster smart-rule child tables point their `roster_id` foreign keys at that root aggregate

## Rollback plan

- Revert the ownership reset together if the roster-global boundary proves incorrectly specified.
- Do not keep draft-owned and roster-owned smart-rule paths alive together as a compatibility
  bridge.
- Preserve the docs/backlog trail so later smart-history and smart-seating work still builds on
  the corrected ownership model.
