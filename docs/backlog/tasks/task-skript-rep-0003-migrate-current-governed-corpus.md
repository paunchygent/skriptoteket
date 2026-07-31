---
type: task
id: TASK-SKRIPT-REP-0003
title: Migrate current governed corpus
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
  approval_evidence: User explicitly approved TASK-SKRIPT-REP-0003 implementation on 2026-07-31
closeout_review:
  record: inline
  status: not_started
task_kind: repository
acceptance_criteria:
- All current governed meaning is migrated to the shared contract.
- Terminal backlog and reviews remain immutable historical evidence and are absent from current relationships, indexes, gates, and lifecycle operations.
- The legacy validator becomes a read-only historical validator and the shared validator is the only current-document authority.
- Same-repository paths are portable while genuine host, container, and cross-repository paths remain explicit.
- The sealed migration plan assigns every candidate exactly once across eight disjoint documentation-specialist slots.
---

## Context

Skriptoteket still has a large legacy governed corpus and validator. The shared
package is installed, the checkout is relocated, and the pre-task audit now
separates current meaning from historical and product-local material. This task
performs the corpus cutover without rewriting terminal history or preserving a
second current governance system.

## Impact And Escalation

The task changes documentation structure, current-document validation,
generated indexes, and backlog identities. It changes no product behavior,
application code, deployment, quality scopes, frontend catalog, or Hemma
operation.

## Decision And Assumption Ledger

| ID | Type | Status | Decision | Source |
| --- | --- | --- | --- | --- |
| MGC-001 | basis | closed | Use clean main `10374578358a4ee82761cc6fa329fa5db941fde0` as the audited source basis and merge later main changes before execution. | Approved identity repair and audit |
| MGC-002 | audit | closed | The complete audit has 1,180 rows: 398 migrate, 764 historical, 9 product-local, 7 replaced, and 2 already current; unresolved count is zero. | Retained audit digest `ee19a78d18b08d6dfdef49cebb7076930b111746a2c514a885af016fed5c5ad0` |
| MGC-003 | cohort | closed | Only the 398 `migrate_current` rows enter package inventory and planning. | Retained cohort digest `d4e8f8b46ff802bfefd56cfea9e4858749f723dad909139339cac4bdefc77cff` |
| MGC-004 | identity | closed | Use the registered `SKRIPT` namespace, preserve Task 0001, reconcile PR-0417 as Task 0002, and map PR-0418 through PR-0421 to Tasks 0003 through 0006. | ST-SKILL-08-06 SKR-004S |
| MGC-005 | history | closed | Terminal sources remain unchanged and current links to terminal or ambiguous legacy identities are removed or mapped to one proven current target. | User approval and audit |
| MGC-006 | ownership | closed | Migrated records use owner `service: skriptoteket`; shared writes and semantic decisions remain parent-owned. | User approval and common contract |
| MGC-007 | lanes | closed | Migrate epic, story, PR/task, changes-requested review, ADR, reference, codemap, PRD, approved mockup, and runbook lanes; keep product material local and replace package-owned templates. | Audit/profile summary |
| MGC-008 | specialists | closed | Run package planning with specialist count 8 and dispatch the exact eight frozen disjoint assignments. | User direction and ST-SKILL-08-06 |
| MGC-009 | validators | closed | Shared validation owns current documents; the local validator is historical-only, read-only, and absent from current gates and generated indexes. | User direction and PR-0418 |
| MGC-010 | package | closed | Select the approved immutable package through executable dependency/lock/runtime evidence; do not pin its version in backlog prose. | ST-SKILL-08-06 package-selection rule |

## Plan

Use the package migration workflow on the sealed cohort, let eight specialists
produce only their frozen candidates, apply centrally, then retire the legacy
current-doc validator path and regenerate the current contract and indexes.

## Implementation Steps

1. Merge current main and prove the selected immutable dependency, lock, and installed runtime.
2. Persist the migration profile and inventory exactly the 398 sealed source paths.
3. Resolve operator inputs from the closed audit and require every candidate to be mechanically mappable or ready to validate.
4. Generate and freeze a plan with specialist count 8; verify unique targets, writes, and complete source coverage.
5. Dispatch the eight package assignments to eight documentation specialists with no shared writes or semantic discretion.
6. Reconcile candidates, run package apply once, and preserve the journal, manifest, diagnostics, and results.
7. Make the historical validator read-only and historical-only; remove it from current gates, indexes, and lifecycle dispatch.
8. Regenerate shared indexes and validate the migrated corpus, path portability, historical immutability, and diff hygiene.

## Proof

- Contract/validator proof: exact audit and cohort digests, package manifest and
  plan coverage, eight disjoint assignments, apply journal, shared current-doc
  validation, and historical-validator isolation.
- Code/search audit: terminal files unchanged; no current relationship targets
  terminal ancestry; no same-repository absolute checkout path; no legacy
  validator in current command, index, hook, or lifecycle routing.
- No behavioral red/green applies to document reshaping. Any validator behavior
  change uses its focused contract tests.

## Validation

- Package migration inventory, classify, plan, candidate, and apply reports.
- `pdm run docs-sync` and `pdm run docs-validate`.
- Focused legacy/current validator tests selected from the changed surface.
- `git diff --check`.

## Stop Conditions

- Source basis or either digest differs.
- Any cohort source lacks one unique target or allowed package classification.
- A current relationship still targets terminal or ambiguous ancestry.
- The plan does not contain exactly eight disjoint assignments covering every candidate once.
- A specialist needs a shared write or semantic decision.
- Apply recovery cannot prove journal/config/source/plan continuity.

## Lessons Learned

Separate the complete disposition audit from the executable migration cohort,
and resolve allocator identities before creating implementation worktrees.

## Notes

The complete audit, cohort, relationship resolution, profile summary, builder,
and checksums are retained under this task's origin planning session.

## Readiness

MGC-001 through MGC-010 are closed. The user approved immediate implementation
and waived another readiness review on 2026-07-31.

## Closeout

Record the independent implementation review, exact validation evidence,
remaining historical-only surfaces, and permitted lifecycle transition.
