---
type: task
id: TASK-SKRIPT-REP-0025
title: Dev tooling command-surface alignment mediation
repository: skriptoteket
owners:
  - kind: service
    id: skriptoteket
created: '2026-07-31'
status: canceled
closeout_review:
  record: inline
  status: not_required
  decided_at: '2026-10-28'
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: 'The user decided on 2026-10-28 (TASK-SKRIPT-REP-0055 D2) to cancel this task as superseded; the Closeout section records what replaced or removed the work.'
task_kind: repository
acceptance_criteria:
  - Given `docs-sync` is a standard docs-as-code closeout command in HuleEdu, Sir Convert-a-Lot, and skill-repository, when Skriptoteket agents inspect the repo command surface, then the absence of `docs-sync` is either corrected with a real generated-docs sync workflow or recorded as an explicit reviewed exception.
  - Given sibling repos separate mutating sync from read-only validation, when Skriptoteket adds or rejects `docs-sync`, then the decision preserves that write/read-only distinction and forbids a no-op alias that masks manual docs upkeep.
  - Given cross-repo tooling should align only where repo semantics match, when this mediation closes, then it records the first implementation slice for Skriptoteket and the separate follow-up candidates for HuleEdu, Sir Convert-a-Lot, and skill-repository without forcing product-specific proof or runtime commands into one shape.
  - Given future implementation must be governed, when any command-surface change is attempted, then the implementer starts from a red proof of the current drift and runs focused tests plus `pdm run docs-validate`, `pdm run handoff-validate` if handoff changes, and `git diff --check` before review.
backlog_document_profile: contract-derived
---

## Implementation Contract

Canceled on 2026-10-28 under TASK-SKRIPT-REP-0055 D2. The original contract below is kept as history; see Closeout.

## Context

Source: `docs/backlog/prs/pr-0409-dev-tooling-command-surface-alignment-mediation.md`. Dev tooling command-surface alignment mediation.

Skriptoteket currently exposes `pdm run docs-validate`, `pdm run handoff-validate`, and `pdm run skills-validate`, but it does not expose `pdm run docs-sync`. HuleEdu, Sir Convert-a-Lot, and skill-repository all use a `docs-sync` surface as part of their docs-as-code workflow. That drift makes daily closeout semantics harder to transfer between repos. It also creates a subtle governance risk: agents can learn that docs changes need a mutating sync pass in sibling repos, then silently skip that step in Skriptoteket because the command is absent. Create a reviewed mediation path for aligning the repo developer command surface, starting with Skriptoteket's missing `docs-sync`. The first impleme

## Impact And Escalation

The source task remains bounded to its repository-owned surface; product behavior or unapproved scope escalates to the parent story/epic.

## Decision And Assumption Ledger

| ID                       | Type      | Status | Question/Assumption              | Recommendation/Decision                                                                            | Source                               |
| ------------------------ | --------- | ------ | -------------------------------- | -------------------------------------------------------------------------------------------------- | ------------------------------------ |
| MIG-TASK-SKRIPT-REP-0025 | migration | closed | How is source meaning preserved? | Preserve the source task contract, current relationships, and status while changing identity only. | ST-SKILL-08-06; TASK-SKRIPT-REP-0003 |

## Contract Inputs

- Source task/PR and audit-approved migration authority.
- Current story or repository relationship in candidate frontmatter.

## Core Vertical And Performance

The source record did not define a separate section for this package heading.

## Plan

Execute only the bounded plan represented by the source record; do not add scope during migration.

## Implementation Steps

1. Preserve the source implementation or proof sequence.
2. Verify current relationships and focused evidence at task closeout.

## Proof

The source proof obligations are retained as historical evidence below; no execution proof is asserted by this candidate.

## Validation

Run the task-selected focused gates and repository docs validation after parent integration.

## Stop Conditions

Stop for missing authority, unresolved identity/relationship, terminal ancestry, or scope expansion.

## Decided Contract Terms

| ID  | Decided contract term                                                                                                                  |
| --- | -------------------------------------------------------------------------------------------------------------------------------------- |
| D1  | Canceled on 2026-10-28 by the user's decision (TASK-SKRIPT-REP-0055 D2); the Closeout section names what replaced or removed the work. |

## Lessons Learned

The source material is retained verbatim below for migration fidelity.

## Notes

### Source evidence

### PR-0409: Dev Tooling Command-Surface Alignment Mediation

### Problem

Skriptoteket currently exposes `pdm run docs-validate`, `pdm run handoff-validate`, and `pdm run skills-validate`, but it does not expose
`pdm run docs-sync`. HuleEdu, Sir Convert-a-Lot, and skill-repository all use a
`docs-sync` surface as part of their docs-as-code workflow.

That drift makes daily closeout semantics harder to transfer between repos. It
also creates a subtle governance risk: agents can learn that docs changes need a
mutating sync pass in sibling repos, then silently skip that step in
Skriptoteket because the command is absent.

### Goal

Create a reviewed mediation path for aligning the repo developer command
surface, starting with Skriptoteket's missing `docs-sync`.

The first implementation decision must choose one of two truthful outcomes:

1. Add a real Skriptoteket `docs-sync` command that mutates generated docs
   surfaces and pair it with read-only freshness validation.
2. Keep Skriptoteket manual for now and document that exception explicitly in
   repo command guidance and shared local-devops references.

The preferred direction is option 1 if Skriptoteket has enough generated docs
surface to justify it. A compatibility alias without generated ownership is not
acceptable.

### Non-goals

- Do not add a no-op `docs-sync` alias.
- Do not implement the command in this planning slice.
- Do not rewrite the whole docs backlog, mockup index, or development changelog.
- Do not change product-specific proof commands, browser auth ceremonies,
  Docker runtime topology, or Hemma deploy lanes.
- Do not normalize repo-specific commands that encode real service differences.

### Exploration Findings

Read-only exploration on 2026-06-29 found:

- Skriptoteket lacks `docs-sync`; its docs command surface currently starts at
  `docs-validate`, `handoff-validate`, and `skills-validate`.
- Skriptoteket already has mature consolidated `dev-stack` and `obs-stack`
  surfaces from `PR-0266`; this task should not reopen that completed Docker
  and observability consolidation.
- skill-repository has the cleanest docs-as-code command shape: a central
  mutating `docs_sync.py` plus read-only `docs_validate.py` freshness checks.
- HuleEdu has the broadest mature implementation: `docs-sync` regenerates
  backlog indexes, workstream hub blocks, research-paper surfaces, lane indexes,
  and the root docs index, with validation recomputing freshness.
- Sir Convert-a-Lot is a compact app-repo reference: `docs-sync` writes generated
  backlog, reference, runbook, and root docs indexes, and `docs-validate`
  checks freshness.
- Other drift candidates exist, but they belong in sibling slices:
  HuleEdu lacks common `lint`, `format`, `typecheck`, and `test` public aliases;
  HuleEdu's BFF OpenAPI export should move away from multi-statement
  `python -c`; frontend typecheck spelling and pre-commit command names are
  lower-risk polish.

### Mediation Decision

The implementation task should use skill-repository's command structure as the
primary shape:

- `docs-sync` is mutating and writes generated artifacts.
- `docs-validate` is read-only and fails when generated artifacts are stale.
- Lower-level helper names may be repo-specific, but the public command intent
  should match sibling repos.

HuleEdu should be used as the maturity reference for edge cases and freshness
checks, not copied wholesale. Its wrapper and broad generated-docs estate are
valid HuleEdu differences.

### Implementation Plan

1. Audit Skriptoteket generated docs candidates:
   `docs/index.md`, `docs/mockups/INDEX.md`, backlog PR/story/epic listings,
   review listings, and any generated reference/runbook surfaces.
2. Decide whether enough surfaces are generated or derivable to justify
   `docs-sync`. If not, write the explicit exception and stop before adding an
   alias.
3. If justified, add a small `scripts.docs_as_code` or equivalent module family
   that keeps sync and validation responsibilities separate.
4. Add `docs-sync` to `pyproject.toml` only after the mutating script has real
   ownership.
5. Add focused tests proving stale generated docs fail validation and that
   `docs-sync` repairs the generated surface.
6. Update repo guidance and shared local-devops references only for the chosen
   public command contract.
7. Record follow-up slices for the HuleEdu quality aliases, HuleEdu BFF OpenAPI
   command cleanup, cross-repo dev-stack semantics documentation, and lower-risk
   frontend/pre-commit naming polish.

### Red-First Proof Plan

The first implementation pass should start with a red proof that represents the
current drift:

- `pdm run docs-sync` is currently absent in Skriptoteket.
- A focused command-surface test should fail until `pyproject.toml` exposes a
  truthful `docs-sync`.
- A generated-freshness test should fail until validation can detect a stale
  generated docs artifact.

The future green proof must show that `docs-sync` repairs the generated artifact
and `docs-validate` remains read-only.

### Test Plan

- Focused command-surface test for the `docs-sync` contract.
- Focused docs freshness tests for any generated index or lane surface.
- `pdm run docs-sync`
- `pdm run docs-validate`
- `pdm run handoff-validate` if `.codex/handoff.md` changes
- `git diff --check`

### Rollback Plan

Remove the planned `docs-sync` implementation and tests, restore the previous
manual-docs guidance, and retain this mediation record as evidence that the
alignment was considered but deferred.

## Readiness

No specialist approval is asserted; parent review remains required.

## Closeout

No closeout evidence is asserted in this candidate.

## Closeout

Canceled on 2026-10-28 under TASK-SKRIPT-REP-0055 D2.

TASK-SKRIPT-REP-0025 is canceled as superseded. Commit 831a44dc9 (2026-10-10) retired `docs-sync` from `pyproject.toml` after repository-governance 0.11.91 folded it into `docs-validate`, and skill-repository exposes the same single `docs-validate` command, so no Skriptoteket-side command-surface drift remains and no alias exists. This note is the recorded exception; the sibling-repo follow-ups (HuleEdu quality aliases, BFF OpenAPI export command) are dropped from this repository's backlog. The task said Skriptoteket never had `docs-sync`; d435a9669 added it and 831a44dc9 removed it. The sibling-repository follow-ups named in the task source were never recorded as backlog items and are dropped.
