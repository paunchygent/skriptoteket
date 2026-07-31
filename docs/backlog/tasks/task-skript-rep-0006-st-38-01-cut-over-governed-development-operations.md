---
type: task
id: TASK-SKRIPT-REP-0006
title: ST-38-01 Cut over governed development operations
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: in_progress
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User approved immediate completion of the cutover on 2026-07-31
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
  - Installed public commands, topology-derived domain/frontend scopes, focused local-producer regressions, current and historical documents, frontend catalog, read-only Hemma transport, deterministic staleness, and root handoff routing pass together.
  - Product, native-library, Docker, deployment, observability, database, migration, worker, runner, auth/Gateway, and lower-level producer behavior remains repository-owned.
  - Only parity-proven shared-workflow overlaps retire; historical evidence stays historical.
dependencies:
  - TASK-SKRIPT-REP-0005
  - TASK-SKILL-08-06-02
---

## Context

Tasks 0003 through 0005 delivered the common current-document contract,
topology-derived quality routing, and shared frontend catalog. This final slice
aligns the installed environment, proves the existing operational surfaces,
corrects active handoff routes, and closes the repository cutover without
redefining product architecture.

## Impact And Escalation

The tracked write set is limited to repository-governance and Hemma facts,
active handoff routes and their preserved budget checker, current cutover
records, root handoff, generated indexes, and any focused regression repair
required to make already-accepted named scopes truthful. Product behavior,
deployment, live services, databases, containers, and historical records remain
unchanged.

## Decision And Assumption Ledger

| ID     | Status | Decision                                                                                                                                                                                                                                                                                                                                                           | Evidence                                     |
| ------ | ------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | -------------------------------------------- |
| GO-001 | closed | No local product or lower-level producer is parity-proven for retirement. The shared routine routes existing producers; it does not replace them.                                                                                                                                                                                                                  | Retirement/preservation Explorer             |
| GO-002 | closed | Preserve the local handoff budget and long-term-memory filename checks, but point their active route and hook at root `handoff.md`. Correct only active route/config/reference pointers; retain historical mentions.                                                                                                                                               | Operations and retirement Explorers          |
| GO-003 | closed | Consumer dependency, lock, installed package, generated bindings, public entrypoints, and the managed Task 0006 worktree must agree at execution time. Exact identity lives in retained evidence, not this backlog prose.                                                                                                                                          | Managed creator and installed identity proof |
| GO-004 | closed | Add Hemma facts for SSH alias `hemma`, checkout `/home/paunchygent/apps/skriptoteket`, and no forwarded environment. Transport proof is read-only Git inspection only.                                                                                                                                                                                             | Shared Hemma Skriptoteket reference          |
| GO-005 | closed | Use HuleEdu's accepted schema-v3 design: declare a unit-test component root and derive its domain scopes from Git topology. Inspect complete, domain, integration, and frontend plans, then execute only the task-relevant domain and frontend names plus focused native-wrapper and stack-dispatcher tests. No explicit domain matrix or unscoped aggregate runs. | HUL-007; user correction on 2026-07-31       |
| GO-006 | closed | Run staleness twice against the immutable task-start revision and fixed date; reports must be byte-identical and leave no repository diff.                                                                                                                                                                                                                         | Operations Explorer                          |
| GO-007 | closed | Shared validation owns current documents; the local historical validator remains manual, read-only, and historical-only.                                                                                                                                                                                                                                           | Task 0003 and validator discovery            |
| GO-008 | closed | Task 0005 and central checkout-path Task 08-06-02 are done with accepted closeout evidence.                                                                                                                                                                                                                                                                        | Current task records                         |

## Plan

Align facts and setup, correct active root-handoff routes while preserving their
budget semantics, inspect installed plans, run only the accepted named/focused
proof, execute read-only Hemma and deterministic staleness proof, validate both
document authorities, and reconcile the task, story, epic, handoff, and derived
indexes.

## Implementation Steps

1. Add exact Hemma facts and include the repository development group in managed setup.
2. Correct active handoff routes and the existing budget hook to root `handoff.md`.
3. Run package-owned setup and prove installed identity, bindings, and managed-worktree admission.
4. Inspect complete, derived domain, integration, and frontend plans before named execution.
5. Run task-relevant domain/frontend scopes and focused native/stack dispatcher regressions.
6. Run read-only Hemma Git inspection and two deterministic staleness reports.
7. Validate current documents, historical documents, frontend catalog/resources, root handoff, active routes, and diff hygiene.
8. Reconcile local cutover lifecycle records and generated indexes.

## Proof

- Package-owned setup, binding validation, and public entrypoint identity pass in the managed worktree.
- Complete topology and the derived governance, scripts, web, and frontend plans are retained before only those task-relevant scopes execute.
- Focused native-library wrapper and `dev-stack`/`obs-stack` dispatcher tests pass.
- `run-hemma` returns only remote root, branch, revision, and clean-state facts.
- Two fixed-basis staleness reports are byte-identical and the repository remains unchanged.
- Current docs validation, historical validation, frontend catalog validation, root handoff validation, active-route audit, and `git diff --check` pass.

## Validation

No unscoped `check`, deploy, restart, container, database, migration, live-stack,
or product browser operation is part of this task.

## Stop Conditions

- A proposed retirement lacks positive semantic parity.
- A named-scope repair would change product behavior or require a compatibility surface.
- Hemma transport would execute anything beyond read-only Git inspection.
- An active-route edit would rewrite historical evidence.
- Installed package, dependency, lock, bindings, or immutable runtime identities disagree after setup.

## Lessons Learned

The final manifest is a small operational checklist and quality-control map.
It preserves repository architecture and names proof; it does not recreate the
repository as governance metadata.

## Notes

Task discovery is retained under the Task 0006 origin session. Shared-package
versions are not pinned in this backlog record.

## Readiness

GO-001 through GO-008 are closed from current repository and central authority.
The user directed the final cutover to proceed without additional ceremony.

## Closeout

Implementation is complete. The consumer uses the approved immutable shared
runtime selected at execution, and the package-generated quality plan derives
the `governance`, `scripts`, and `web` unit scopes from tracked Git topology.
The existing frontend producer remains its own named scope. No explicit domain
matrix or unscoped aggregate was introduced or executed.

Focused proof passed:

- package setup, installed identity, binding validation, and plan inspection;
- typed `governance` (2 tests), `scripts` (176 tests), and `web` (424 tests)
  checks;
- frontend typecheck and 1,300 frontend tests across 229 files;
- 16 native-wrapper and stack-dispatcher tests, 16 linter tests, and 23 focused
  Exam Converter tests;
- read-only Hemma Git transport and two byte-identical fixed-basis staleness
  reports;
- shared current-doc validation, manual historical-only validation, root
  handoff validation, active-route audit, lock consistency, and diff hygiene.

The commit hook retains staged formatting, linting, document, handoff, and
frontend lint gates. Typed tests run through the topology-derived named scopes;
the hook does not invoke an unscoped repository typecheck or test aggregate.

Product runtime behavior, deployment, databases, containers, migrations,
workers, authentication, and lower-level producers remain repository-owned.
No overlap was retired because no local producer had positive parity proof.
Terminal backlog and historical references remain historical.
