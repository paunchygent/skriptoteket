---
type: task
id: TASK-SKRIPT-19-07-01
title: 'Story 003c: thin adapter parity and demanding scientific PDF workload validation'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-19-07
task_kind: story
acceptance_criteria:
- Skriptoteket provider-side adapter behavior is verified against canonical Story
  003c contract semantics, with no HuleEdu-specific logic forks.
- End-to-end HuleEdu consumer flow (submit, poll, retrieve) runs against Skriptoteket
  without per-document converter code changes.
- Demanding scientific-paper workload evidence is produced with per-document status,
  duration distribution (min/p50/p95/max), and failure taxonomy mapped to canonical
  error codes.
- Story/PR docs link to provider + consumer evidence artifacts sufficient to support
  Story 003c closure review.
dependencies:
- ST-SKRIPT-19-07
---

## Context

### Source: Problem

Story 003c closure requires proof that the provider side (Skriptoteket) remains contract-faithful and
easy to consume from HuleEdu for demanding scientific-paper PDF workloads. Existing artifacts do not
yet provide a closure-ready, cross-repo evidence package.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Story Contract Slice

### Source: Goal

- Validate Skriptoteket thin-adapter behavior against canonical Story 003c semantics.
- Demonstrate consumer ergonomics from HuleEdu with no per-document special cases.
- Produce a reproducible evidence package for demanding scientific-paper corpus runs.
- Link evidence into docs for closure readiness.

## Contract Inputs

The source does not record separate contract inputs.

## Plan

### Source: Implementation plan

1. Confirm provider-side adapter semantics are canonical and thin:
   - review adapter boundary and contract surface behavior in Skriptoteket.
   - document invariants and any required cleanup to remove consumer-specific branching.
2. Execute end-to-end consumer validation from HuleEdu against Skriptoteket:
   - submit, poll, and retrieve for representative documents.
   - capture command set and environment assumptions.
3. Run demanding scientific-paper workload validation:
   - source corpus from
     `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`.
   - collect per-document outcomes, timings, and canonical error mapping.
4. Update docs in both repos with evidence links and closure notes.

## Implementation Steps

The source does not provide separate implementation steps.

## Proof

### Source: Test plan

- Skriptoteket repo:
  - `pdm run docs-validate`
  - `pdm run pytest tests/integration --override-ini "addopts=-s -v --durations=10 --log-cli-level=INFO --import-mode=importlib"`
- HuleEdu repo:
  - adapter-path integration tests
  - end-to-end smoke against Hemma tunnel/service
  - workload execution commands for the scientific-paper corpus

## Validation

### Source: Test plan

- Skriptoteket repo:
  - `pdm run docs-validate`
  - `pdm run pytest tests/integration --override-ini "addopts=-s -v --durations=10 --log-cli-level=INFO --import-mode=importlib"`
- HuleEdu repo:
  - adapter-path integration tests
  - end-to-end smoke against Hemma tunnel/service
  - workload execution commands for the scientific-paper corpus

## Stop Conditions

### Source: Non-goals

- Implementing HuleEdu business logic inside Skriptoteket.
- Introducing fallback contract variants or compatibility shims.
- Per-document converter code edits to complete the workload.

## Lessons Learned

The source does not record separate lessons learned.

## Notes

### Source: Rollback plan

- Revert documentation artifacts (`TASK-SKRIPT-19-07-01`, any linked story/epic note edits) if scope or contract target changes.
- Keep runtime behavior unchanged unless explicitly modified in follow-up implementation PRs.

## Plan Document Review

The source does not include a plan document review record.

## Implementation Review

The source does not include an implementation review record.
