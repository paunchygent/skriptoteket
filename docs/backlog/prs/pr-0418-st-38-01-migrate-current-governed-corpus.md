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

- the per-executable-slice rule requiring the currently approved immutable
  `repository-governance` release to be selected at execution start, with its
  exact consumer dependency, lock, and installed identity recorded in retained
  execution evidence, and its explicit positive specialist-count contract,
  including proof that the count is supplied by the parent and that no fixed
  five-specialist fallback remains;
- the complete post-PR-0417 source cohort with source hashes and one exact
  sealed manifest; every source has one disposition, including current
  migration, historical preservation, or an explicitly classified omission;
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

1. Verify the immutable 0.9.3 producer and its parent-supplied positive
   specialist-count contract before inventory; stop if the release or contract
   proof is absent.
2. Inventory the exact post-PR-0417 basis and freeze every governed source in
   one sealed manifest with a disposition for every source.
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
- Immutable 0.9.3 producer/version/revision and positive specialist-count
  admission proof.
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
- The immutable 0.9.3 producer, peeled revision, or explicit positive
  specialist-count contract is missing or differs from the sealed manifest.
- A current relationship depends on terminal ancestry without explicit repair.
- The legacy validator can mutate, transition lifecycle, populate generated
  indexes, or enter any current gate.
- A specialist needs a shared write or semantic decision.
- The migration would treat the local authority-spine records as permission
  to reopen or retroactively authorize the PR-0417 bootstrap.
