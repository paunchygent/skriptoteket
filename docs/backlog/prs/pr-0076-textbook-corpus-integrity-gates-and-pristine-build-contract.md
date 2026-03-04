---
type: pr
id: PR-0076
title: "Textbook corpus — integrity gates and pristine build contract"
status: ready
owners: "agents"
created: 2026-03-04
updated: 2026-03-04
stories:
  - "ST-22-01"
tags: ["data", "quality", "validation"]
acceptance_criteria:
  - "Pristine build is blocked if critical unresolved issues remain."
  - "Integrity validators cover section continuity, page-anchor continuity, task numbering continuity, and answer-key mapping coverage."
  - "Build outputs include machine-readable validation report and human-readable checklist."
---

## Problem

Without hard gates, a corpus can look clean but still be broken for retrieval and teaching use.

## Goal

Define and enforce deterministic quality gates that must pass before the corpus is considered pristine.

## Non-goals

- No embedding/vector ingestion in this slice.

## Implementation plan

1. Implement integrity validators with strict failure levels.
2. Define acceptance thresholds and unresolved-issue policy.
3. Produce `pristine` artifact only when validators pass.
4. Emit report outputs for audit and manual verification.
5. Add regression tests for validator behavior.

## Test plan

- Unit tests for each validator.
- End-to-end dry run from mechanical + manual patches to pristine build.
- Negative tests that ensure gate failures block promotion.

## Rollback plan

- Remove pristine/gate outputs from this slice.
- Keep prior restoration state and rerun after fixes.
