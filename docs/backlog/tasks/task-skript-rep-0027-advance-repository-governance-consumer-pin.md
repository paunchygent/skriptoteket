---
type: task
id: TASK-SKRIPT-REP-0027
title: Advance repository-governance consumer pin
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-08-01'
status: done
readiness_review:
  record: inline
  status: approved
  reviewer: plan-document-reviewer
  decided_at: '2026-08-01T01:54:29+02:00'
closeout_review:
  record: inline
  status: approved
  reviewer: ruthless-code-review
  decided_at: '2026-08-01T02:02:49+02:00'
  approval_protocol: agent-overseer:approved-review-closeout
  approval_evidence: Inline review approved candidate 0c80b3aa6f974106aaf724b69cd61fbffea6dc9e
task_kind: repository
acceptance_criteria:
- Given the user-approved immutable repository-governance release, when Skriptoteket
  advances its governed tooling dependency, then the approved peeled revision is pinned
  and locked, unchanged generated bindings are synchronized, focused identity and drift
  checks pass, and no product behavior changes.
---

## Context

Skriptoteket completed its governed-development cutover against the previously
approved immutable package release. The shared package now has a newer
user-approved immutable release whose publication behavior must be adopted by
an ordinary consumer pin and lock advance. The current dependency, lock, and
installed package identity still resolve to the previous release.

## Impact And Escalation

The task affects only the repository-governance dependency pin, its PDM lock
record, and the package-owned generated binding blocks. Product source,
frontend resources, backlog migration, quality topology, deployment, databases,
and Hemma operations are outside scope.

## Decision And Assumption Ledger

| ID | Status | Contract term, decision, or assumption | Recommendation or closed decision | Other highly plausible options | Motivation | Source |
| --- | --- | --- | --- | --- | --- | --- |
| PIN-001 | closed | Which shared package release is the consumer target? | Adopt the exact user-approved immutable release and its peeled revision; do not follow `origin/main`. | Keep the previous immutable release. | The user explicitly requested the pin advance, while the immutable revision preserves reproducibility. | User instruction in the current Codex task on 2026-08-01; central immutable-release handoff. |
| PIN-002 | closed | What may change in Skriptoteket? | Change only the dependency pin and lock, run the package-owned binding synchronizer, and retain a binding delta only if the synchronizer produces one. | Broaden the update into product, quality-topology, docs-corpus, or operational changes. | The package binding maps are unchanged and the requested outcome is dependency adoption, not another cutover. | Retained discovery `repository-governance-0-9-7-pin/0001`; completed `TASK-SKRIPT-REP-0006`. |
| PIN-003 | closed | What proves the update? | Validate the central immutable runtime, update only the named dependency group without syncing, install from the resulting lock, check lock freshness, installed package identity and VCS revision, generated-binding drift, the bounded file set, and whitespace. | Run broad backend or frontend tests. | This is package metadata and generated-binding adoption; product tests cannot add relevant confidence and would violate the service-driven check policy. | Retained discovery `repository-governance-0-9-7-pin/0001`; shared proof-selection contract. |
| PIN-004 | closed | Does behavioral red/green apply? | Use contract and validator proof; behavioral red/green does not apply because the task changes dependency identity without adding consumer behavior. | Add a test that pins a release literal. | Literal-pinning tests are forbidden and would test implementation metadata rather than a behavioral boundary. | Shared proof-selection contract; repository prohibition on prose- and log-pinning tests. |

## Plan

Replace the single repository-governance Git revision in the
`monorepo-tools` dependency, update only that package in the same PDM group with
reuse and no install, synchronize the package-owned bindings, then install and
run the focused identity and drift checks. Preserve the synchronizer result
truthfully; the expected binding delta is empty.

## Implementation Steps

1. Validate the user-approved immutable central runtime and record its peeled
   revision as the dependency target.
2. Replace the one Git revision in `pyproject.toml` and run
   `pdm update -G monorepo-tools --update-reuse --no-sync repository-governance`.
3. Synchronize the marked repository-governance binding blocks through the
   package-owned synchronizer, then install the declared frozen groups.
4. Run the focused lock, package-identity, VCS-revision, binding-drift,
   bounded-diff, docs, and whitespace checks.
5. Obtain independent implementation review, integrate the exact reviewed head
   into current `main`, publish, and retire the task worktree and branch.

## Proof

- Mode: contract and validator proof. Behavioral red/green does not apply to
  the dependency-identity update.
- Pre-change: package identity and VCS metadata resolve to the previous
  immutable release; the central runtime validates the user-approved target.
- Post-change: `pdm lock --check`, installed package version and VCS revision,
  `pdm run repository-governance-bindings check --project-file pyproject.toml`,
  and the bounded Git diff all agree with the user-approved immutable target.

## Validation

- Central runtime identity validation for the user-approved immutable tuple.
- `pdm lock --check`.
- Installed `repository-governance --version` plus installed VCS metadata.
- `pdm run repository-governance-bindings check --project-file pyproject.toml`.
- `pdm run docs-validate` because this task record changes.
- `git diff --check` and a changed-file audit limited to the governed task,
  generated repository index, dependency pin, lock, and any synchronizer-owned
  binding delta.

## Stop Conditions

- Stop for an immutable-runtime identity mismatch, lock changes outside the
  named package and required metadata hash, any product-source change, a
  generated-binding change not produced by the synchronizer, or a failed
  focused proof that requires broader authority.

## Lessons Learned

The package-owned exact-pin recovery command currently assumes a dependency
group named `tooling`; Skriptoteket uses `monorepo-tools`. This task uses PDM's
bounded named-group update instead of changing either public contract.

## Notes

The local frontend frozen-install initially stopped for an interactive
`node_modules` replacement. Running the exact frozen install once with explicit
confirmation repaired the untracked environment; the sanctioned bootstrap then
completed without tracked changes.

## Readiness

PIN-001 through PIN-004 are closed by the user's instruction, immutable-release
handoff, current repository discovery, and shared proof rules. Independent plan
review owns the readiness verdict. The only residual risk is an unexpected
transitive lock delta; the stop condition prevents absorbing it.

User closure: `agent-planning:user-closure-gate`; the user's explicit pin
instruction authorizes this bounded task plan.

## Plan Document Review

- Recorded: `2026-08-01T01:54:29+02:00` (`CEST`).
- Reviewer: `plan-document-reviewer`.
- Decision: `approved`.
- Reviewed scope:
  `docs/backlog/tasks/task-skript-rep-0027-advance-repository-governance-consumer-pin.md`,
  limited to readiness of the standalone repository-task plan.
- Governing authority: the user's instruction to adopt the newly approved
  immutable repository-governance release; the central immutable-release
  handoff; retained discovery
  `discovery/explorer/repository-governance-0-9-7-pin/0001-pin-lock-bindings-proof.md`;
  completed `TASK-SKRIPT-REP-0006`; and the canonical repository-task,
  decision-ledger, proof-selection, review-gate, and worktree-lifecycle
  contracts.
- Findings: none. The task is a single-responsibility consumer pin, lock, and
  package-owned binding-sync slice. PIN-001 through PIN-004 close the material
  decisions; the implementation surfaces, focused contract/validator proof,
  validation, non-goals, and stop conditions are aligned with the accepted
  authority. No walking-skeleton or product test is required because the task
  adds no product behavior or cross-system behavior boundary.
- Permitted next step: the owning parent may apply `proposed -> ready`, refresh
  generated projections, validate and publish the ready plan, and retire the
  planning worktree. Implementation of this task requires a later, separate
  governed admission.
- Residual risk: implementation proof has not run. The exact PDM lock delta and
  expected no-op binding synchronization remain to be observed; the task stops
  on an unexpected transitive lock, product-source, or non-synchronizer-owned
  binding change. The reviewer ran `git diff --check` on the tracked planning
  delta and a direct trailing-whitespace scan on this untracked renamed task
  file successfully, but did not run docs sync or docs validation because
  generated projections and lifecycle changes remain parent-owned after this
  reviewer-only write.

## Closeout

Implementation evidence prepared for independent review:

- The central runtime validated the user-approved immutable package identity.
- The PDM update changed only the repository-governance lock record and the
  lock content hash; no unrelated dependency moved.
- The package-owned binding synchronizer produced no tracked binding delta,
  and its read-only drift check passed.
- Frozen setup completed for the declared Python groups and frontend workspace.
- `pdm lock --check`, installed package version, installed VCS metadata,
  `pdm run repository-governance-bindings check --project-file pyproject.toml`,
  `pdm run docs-validate`, and `git diff --check` passed.
- The implementation write set is limited to `pyproject.toml`, `pdm.lock`, this
  task record, and the generated repository index.
- No product, backend, frontend, broad repository, deployment, database, Hemma,
  or browser check ran because none is applicable to this metadata-only pin
  advance.

Independent implementation review:

- Recorded: `2026-08-01T02:02:49+02:00` (`CEST`).
- Reviewer: `ruthless-code-review`.
- Decision: `approved`.
- Reviewed scope: exact candidate
  `0c80b3aa6f974106aaf724b69cd61fbffea6dc9e` against base
  `9ef1087096cee9a136ed0ca6c8185167477668e0`, limited to this task
  record, `docs/repository-index.json`, `pyproject.toml`, and `pdm.lock`.
- Governing authority: acceptance criteria and closed ledger decisions PIN-001
  through PIN-004, including the exact user-approved immutable release and
  peeled revision, the bounded dependency/lock and synchronizer-owned write
  surface, and contract/validator proof without product tests.
- Findings: none. The source dependency and lock package record agree on the
  approved peeled revision; the package record advances coherently; the only
  other lock change is the required content hash. No binding or product delta
  exists. At the candidate head, the generated index truthfully reflects the
  implementation-owned source lifecycle, and the backlog prose does not
  hardcode the shared package version or revision. The parent-owned projection
  refresh must incorporate this reviewer-owned approval.
- Permitted next step: the owning parent may preserve this approval, apply the
  authorized closeout lifecycle transition, refresh generated projections,
  validate, integrate the exact reviewed candidate into current `main`, and
  publish through the governed merge-only workflow.
- Residual risk: the review relies on the supplied successful immutable-runtime,
  frozen-bootstrap, lock, installed-identity, VCS-revision, binding-drift,
  docs-validation, changed-file, and whitespace evidence. No product behavior
  changed, so no product-runtime risk was introduced by this slice.
- Validation not run by reviewer: supplied routine gates were not duplicated;
  backend, frontend, browser, deployment, database, Hemma, and broad repository
  checks remain outside this task's accepted proof scope.
