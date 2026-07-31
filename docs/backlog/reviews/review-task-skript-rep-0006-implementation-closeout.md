---
type: review
id: REV-SKRIPT-TASK-REP-0006-CLOSEOUT
title: 'Review: TASK-SKRIPT-REP-0006 implementation closeout'
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-08-01'
status: changes_requested
target: TASK-SKRIPT-REP-0006
gate: closeout
reviewer: ruthless-code-review
decided_at: '2026-08-01T00:43:44+02:00'
---

## Governing Authority

`TASK-SKRIPT-REP-0006`, including closed decisions GO-001 through GO-008 and
the task stop conditions, governs this closeout gate. This review assesses
candidate `474679f5a68dfa339dd8ce2f94d8dfd8fe2637f9` against parent
`1cdff06d3f238d916b157cee95bc40ab8fa8cd07` for the named next step of
implementation closeout and integration to local `main`.

## Reviewed Scope

- The exact committed 42-file diff and the changed configuration, source,
  tests, current docs, handoff routes, dependency lock, and generated index
  claims.
- The retained Task 0006 context, index, three task-root discovery records,
  governing task ledger, review persistence contract, proof-selection rules,
  and forbidden-pattern/typing rules.
- The supplied successful governance, scripts, web, frontend, native/stack,
  linter, Exam Converter, docs, Hemma, staleness, lock, route, and diff evidence.
- Routine successful gates were not rerun. Lifecycle status, generated indexes,
  handoff, implementation, and test files were not changed by this reviewer.

## Evidence

- `git show -s --format='%H %P %s' 474679f5` identifies the exact candidate and
  parent named above; `git diff --name-status 474679f5^ 474679f5` identifies the
  reviewed change set.
- The governing task limits focused regression repair to changes that preserve
  product behavior and stops when a named-scope repair would change product
  behavior (`docs/backlog/tasks/task-skript-rep-0006-st-38-01-cut-over-governed-development-operations.md:39`,
  `docs/backlog/tasks/task-skript-rep-0006-st-38-01-cut-over-governed-development-operations.md:95`).
- Retained discovery records the conversion-route help decision as unresolved
  and distinguishes the generic `apps_detail` topic from route-specific
  conversion guidance
  (`.orchestration/context/tasks/TASK-SKRIPT-REP-0006/discovery/explorer/task0006-frontend-contract-diagnosis/0001-linter-and-help-route-failure-root-causes.md`).
- Global policy and the ruthless review typing contract forbid `object` as a
  typing escape hatch.

## Findings

### Blocker — the typed scripts proof introduces a forbidden `object` escape hatch

`tests/unit/scripts/test_story58_artifact_set_invariants.py:32` adds
`_is_invariant_summary(value: object)`. The global repository policy expressly
forbids `object`, and the review contract makes `Any`, `cast`, `object`, type
ignores, and runtime duck-typing used to bypass contracts blockers. This helper
was added specifically to make the newly selected scripts typecheck pass, so
the green typecheck does not satisfy the task's narrow-typing requirement.

Required fix: replace the `object` input with an explicit repository-permitted
type that represents the accepted summary input and preserves truthful runtime
narrowing. Rerun only the affected typed `scripts` named check and focused
invariant tests.

### High — frontend proof repair changes product help behavior outside the closed ledger

`frontend/apps/skriptoteket/src/components/help/helpTopicCatalog.ts:103` adds a
new user-visible `my_runs` topic, while lines 156-160 map three authenticated
conversion routes and two internal inspection routes to the generic
`apps_detail` product topic. `helpTopics.ts` and `HelpTopicMyRuns.vue` make the
new topic live. These are product help resolution and content changes, not
test-fixture repairs. The task's Impact And Escalation boundary keeps product
behavior unchanged, and its stop condition requires implementation to stop if
a named-scope repair would change product behavior. Retained discovery also
left the conversion-topic mapping decision unresolved; the closed GO-001
through GO-008 ledger never selects this fallback.

Required fix: remove the product help behavior changes from this candidate and
keep any frontend repair within test/fixture scope. If the named frontend check
cannot remain truthful without changing help behavior, return to planning or
the user to close the route-topic authority gap in a separate product task;
do not select a fallback mapping inside Task 0006.

## Decision

`changes_requested`

## Permitted Next Step

Correct the two findings and request rereview of only the files changed after
this decision. Integration to `main` is not permitted while these findings
remain open.

## Validation Not Run

The new retained record passed targeted
`pdm run docs-validate docs/backlog/reviews/review-task-skript-rep-0006-implementation-closeout.md`;
its generated-index side effect was removed because this assignment forbids
generated-index changes. No implementation lint, format, typecheck,
docs-validation, test, frontend build, Hemma, or staleness command was rerun
because the parent supplied successful evidence and the review contract
prohibits duplicating it solely for review. No live browser proof was run
because product browser operation is outside Task 0006.

## Residual Risk

Seven tracked Python test files remain directly under `tests/unit` and therefore
outside the component-root child domains, as retained discovery records. The
closed ledger authorizes topology-derived named domain checks rather than a
separate root-file cohort or unscoped aggregate, so this is a non-authorizing
residual coverage risk rather than a required Task 0006 change.
