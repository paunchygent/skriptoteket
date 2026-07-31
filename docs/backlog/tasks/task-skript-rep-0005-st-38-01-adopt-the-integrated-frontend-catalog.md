---
type: task
id: TASK-SKRIPT-REP-0005
title: ST-38-01 Adopt the integrated frontend catalog
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: done
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User approved immediate implementation on 2026-07-31
closeout_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: User directed completion without further ceremony on 2026-07-31
task_kind: repository
acceptance_criteria:
  - The root facts declare the accepted frontend workspace and central design-resource contract, and the central tool owns only its reserved catalog block.
  - The app consumes all 17 shared dependencies through the catalog while its manifest, lockfile, source, styles, and components remain repository-owned.
  - The three shared resource metadata files match central authority without replacing Skriptoteket product resources.
dependencies:
  - TASK-SKRIPT-REP-0004
---

## Context

The frontend already uses the shared PNPM version and declares the complete
17-package integrated frontend cohort, but it still repeats local version ranges
and has no declared central resource contract. This task adopts the central
catalog as dependency coordination and quality control. It does not redesign or
replace Skriptoteket's frontend.

## Impact And Escalation

The write set is limited to frontend governance facts, the reserved workspace
catalog block, the app dependency specifiers, its lockfile closure, three new
resource metadata files, and this task's docs. Product source, CSS, components,
Docker, backend, deployment, auth, and observability remain unchanged.

## Decision And Assumption Ledger

| ID     | Status | Decision | Evidence |
| ------ | ------ | -------- | -------- |
| FC-001 | closed | The workspace is `frontend/pnpm-workspace.yaml`; dependency manifests are `frontend/package.json` and `frontend/apps/skriptoteket/package.json`; the consumer lock is `frontend/pnpm-lock.yaml`. | Consumer Explorer |
| FC-002 | closed | All 17 app dependency names already match the central catalog and will use `catalog:`. The central synchronizer owns only its reserved workspace block. | Central and consumer Explorers |
| FC-003 | closed | Store the shared resource metadata contract at `frontend/apps/skriptoteket/src/design-system/huleedu-integrated/` and copy only `manifest.json`, `manifest.schema.json`, and `package.json`. | HuleEdu consumer pattern and user direction |
| FC-004 | closed | Skriptoteket continues to own its app manifest, lockfile, product source, styles, and components. Divergent product resource files are not overwritten. | Consumer digest comparison |
| FC-005 | closed | No catalog exceptions are required. | Exact dependency-name comparison |
| FC-006 | closed | The accepted lock change is only catalog adoption closure; the expected material resolution change is the Vue Vite plugin aligning with central authority. | Lockfile comparison |
| FC-007 | closed | Proof uses central sync/read-only validation, metadata equality, frozen PNPM install, frontend typecheck, focused resource-component Vitest, build, docs validation, and diff hygiene. | User-approved bounded proof |

## Plan

Synchronize the reserved catalog block, replace the app's 17 repeated version
ranges with catalog references, add the three shared resource metadata files,
and regenerate only the resulting lockfile closure.

## Implementation Steps

1. Declare the resource manifest and package in root frontend facts.
2. Synchronize the central reserved catalog block.
3. Adopt `catalog:` for the exact 17 app dependencies.
4. Add the three shared resource metadata files and regenerate the bounded lock closure.
5. Run the focused contract and frontend proof.

## Proof

- Central catalog synchronization is idempotent and read-only validation passes.
- Consumer resource metadata matches the central files exactly.
- Frozen PNPM install, frontend typecheck, focused Vitest, and build pass.
- Docs validation and `git diff --check` pass.

## Validation

No broad frontend suite, unscoped repository check, product behavior change, or
full central resource-tree copy is authorized.

## Stop Conditions

- Synchronization changes anything outside its reserved workspace block.
- Lockfile churn exceeds the 17 catalog dependencies and their required closure.
- Adoption requires replacing Skriptoteket CSS, components, or runtime source.
- The immutable central runtime and central resource authority disagree.

## Lessons Learned

The catalog manifest organizes dependency work and provides quality control. It
must stay smaller than the frontend it describes and must not become a second
architecture model.

## Notes

Discovery is retained under the Task 0005 task root and its origin planning
session. No shared-package version is pinned in this backlog record.

## Readiness

FC-001 through FC-007 are closed. The user approved implementation and directed
this step to proceed without additional ceremony.

## Closeout

The immutable synchronizer added only its reserved 17-entry catalog block, and
all 17 matching app dependencies now use `catalog:`. The lockfile changed only
for catalog metadata, importer specifiers, and the required Vue Vite plugin
upgrade with its plugin utility dependency. A second synchronization was
unchanged, catalog validation passed, and frozen PNPM installation succeeded.

The three consumer resource metadata files are byte-identical to central
authority. No product source, CSS, components, or other resource exports were
copied or changed. Frontend typecheck, five focused tests across three UI
primitive files, and the production build pass. Docs validation and diff
hygiene cover the governed closeout surfaces. The broad frontend suite was not
rerun; Task 0004's six unrelated product/test failures remain explicit debt.
