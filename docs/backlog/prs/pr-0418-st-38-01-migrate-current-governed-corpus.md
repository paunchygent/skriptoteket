---
type: pr
id: PR-0418
title: "ST-38-01 Migrate the current governed corpus"
status: blocked
owners: "agents"
created: 2026-07-31
updated: 2026-07-31
stories:
  - "ST-38-01"
dependencies:
  - "PR-0417"
  - "TASK-SKILL-08-06-01"
tags: ["repository-governance", "docs-as-code", "migration"]
acceptance_criteria:
  - "Every current authoritative reference, ADR, runbook, and nonterminal backlog record migrates to the common contract through one exact sealed manifest."
  - "Every other governed source receives an explicit disposition, terminal backlog and terminal reviews remain historical, and duplicate identities are resolved before candidates."
  - "Active validation uses the shared current contract; any legacy validator is read-only historical inspection outside active gates, generated indexes, and lifecycle transitions."
  - "Current internal links are repository-relative and specialists use every available disjoint child assignment while the parent owns shared writes."
---

## Problem

The legacy corpus contains 1,196 governed records, unsupported lanes, seven
duplicate-ID groups, PR/review dependencies, and machine-local paths.

## Goal

Replace the legacy current graph with one complete common-contract graph
without promoting terminal history, creating dual validation authority, or
retroactively authorizing the bootstrap exception.

## Admission gate

This PR remains a non-authorizing planning envelope and remains blocked until
the parent attaches all of the following accepted inputs; specialists cannot
supply or infer them:

- an independently approved `TASK-SKRIPT-REP-0003` contract that records the
  closed audit, cohort, identity, relationship, profile, ownership, proof,
  recovery, and stop-condition decisions and has completed its separate
  readiness transition;
- the per-executable-slice rule requiring the currently approved immutable
  `repository-governance` release to be selected at execution start, with its
  exact consumer dependency, lock, and installed identity recorded in retained
  execution evidence, and its explicit positive specialist-count contract,
  including proof that the count is supplied by the parent and that no fixed
  five-specialist fallback remains;
- a complete post-PR-0417 source-disposition audit with source hashes and one
  authority-backed disposition for every governed source; the audit separates
  current migration from historical preservation, product-local retention,
  replacement, and explicitly classified omission;
- one exact executable cohort containing only the audit's current-migration
  rows; the package manifest must seal exactly this cohort and must not encode
  historical, product-local, replaced, or omitted sources as migration
  candidates;
- unique source-to-target identities and paths, `retired_ids`, document kind,
  reference classification and summary, owner, parent, authority evidence,
  review target, dependency batch, and canonical write set;
- explicit terminal dispositions keeping terminal backlog items and terminal
  reviews historical, with any current relationship that names terminal
  ancestry repaired before candidates; and
- disjoint specialist assignments for every available child slot, while the
  parent retains the manifest, decisions, shared records, generated indexes,
  apply/recovery, Git, and integration.

The local EPIC/ST/PR authority-spine records and their legacy fields are part
of this migration cohort when nonterminal; migrating them establishes their
current common-contract identities and does not retroactively authorize the
PR-0417 one-time direct-`main` bootstrap, which remains governed only by its
own accepted review and proof.

## Implementation plan

1. Select the currently approved immutable producer at execution start and
   verify its exact consumer dependency, lock, installed identity, and
   parent-supplied positive specialist-count contract before inventory; stop
   if any tuple member or contract proof is absent.
2. Audit the exact post-PR-0417 governed-source basis and freeze one explicit
   disposition for every source. Derive the executable current-migration cohort
   from that complete audit and seal only that cohort in the package manifest.
3. Resolve duplicate IDs and all current source-target identities before
   candidates, including authority-spine local legacy fields.
4. Classify every lane and path; migrate current references, ADRs, runbooks,
   and nonterminal backlog records, while keeping terminal backlog/reviews
   historical and repairing terminal-ancestry dependencies explicitly.
5. Make the shared current validator the sole active gate/index/lifecycle
   authority; retain any legacy validator only as immutable read-only
   historical inspection outside those surfaces.
6. Use every available specialist slot on disjoint candidates, with the parent
   owning all shared writes and semantic decisions.
7. Run plan, dry-run, sealed apply, validate, report, one docs synchronization,
   and a clean read-only rerun.

## Test plan

- Migration manifest/identity/disjointness/relationship proof.
- Selected immutable producer/version/revision and positive specialist-count
  admission proof retained as execution evidence rather than backlog policy.
- Shared current validator proof and legacy-validator historical-only,
  no-mutation, no-gate, no-index, and no-lifecycle proof.
- Complete source disposition audit, including terminal backlog/review
  preservation and authority-spine migration without bootstrap authorization.
- Repository-relative current-link audit and classified external paths.
- `pdm run docs-sync`, `pdm run docs-validate`, and `git diff --check`.

## Rollback plan

Use producer-owned automatic restoration or explicit recover/resume only.
Preserve manifest, seal, journal, results, diagnostics, and canonical diff.

## Stop conditions

- Any source lacks an authority-backed disposition or unique target.
- The central identity-repair draft is not independently approved, current
  `main` has not been merged into this planning branch, or the public allocator
  cannot create `TASK-SKRIPT-REP-0003` from the integrated current graph.
- The selected immutable producer tuple or explicit positive specialist-count
  contract is missing or differs from retained execution evidence or the
  sealed manifest.
- A current relationship depends on terminal ancestry without explicit repair.
- The legacy validator can mutate, transition lifecycle, populate generated
  indexes, or enter any current gate.
- A specialist needs a shared write or semantic decision.
- The migration would treat the local authority-spine records as permission
  to reopen or retroactively authorize the PR-0417 bootstrap.
