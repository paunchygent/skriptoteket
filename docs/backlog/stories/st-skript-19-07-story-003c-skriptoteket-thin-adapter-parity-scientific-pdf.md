---
type: story
id: ST-SKRIPT-19-07
title: 'Story 003c: Skriptoteket thin adapter parity + scientific PDF workload validation'
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
epic: EPIC-SKRIPT-19
acceptance_criteria:
- Given HuleEdu integrates through the canonical Story 003c adapter contract, when
  requests reach Skriptoteket, then adapter handling remains thin and contract-faithful
  with no HuleEdu-specific logic forks in Skriptoteket.
- Given demanding scientific-paper PDFs are submitted from the HuleEdu integration
  path, when workloads execute end-to-end (submit, poll, retrieve), then outcomes
  are surfaced via canonical status and structured error surfaces without per-document
  code changes.
- Given a representative scientific-paper corpus is executed, when validation completes,
  then evidence includes per-document status, duration distribution (min/p50/p95/max),
  and failure taxonomy mapped to canonical error codes.
- Given Story 003c closure review, when reviewers inspect Skriptoteket docs, then
  this story and linked evidence clearly support closure readiness from the provider
  side.
retired_ids:
- ST-19-07
---

## Context

### Source: Context

This story is the Skriptoteket-side parallel to HuleEdu consumer adoption work for Story 003c.
The goal is to prove the provider side remains easy to consume for demanding scientific-paper PDF
workloads without introducing consumer-specific branches in Skriptoteket.

## Epic Contract Slice

### Source: Scope

- Align/confirm Skriptoteket adapter behavior against canonical Story 003c contract semantics.
- Validate the end-to-end consumer path from HuleEdu against Skriptoteket service surfaces.
- Capture provider-side workload evidence for a representative demanding scientific-paper corpus.
- Publish closure-ready evidence links in Skriptoteket docs.

## ADR Coverage

The source does not provide a separate adr coverage section; no additional adr coverage is recorded.

## Contract Inputs

The source does not provide a separate contract inputs section; no additional contract inputs is recorded.

## Live Verification Plan

### Source: Workload Validation Requirements

- Corpus profile:
  - Real, non-sensitive scientific papers with mixed complexity (figures, tables, multi-column
    text, references, appendices).
  - Representative page-count spread for demanding workloads.
  - Default consumer source path in HuleEdu repo:
    - `/Users/olofs_mba/Documents/Repos/huledu-reboot/docs/research/research_papers/llm_as_a_annotater`

- Operational behavior:
  - Submit, poll, and retrieve flows must run without converter code edits across documents.
  - Failures (if any) must surface through canonical status/error surfaces with actionable
    diagnostics.

### Source: Evidence Package

- Per-document status summary.
- Duration distribution summary (min/p50/p95/max).
- Failure taxonomy mapped to canonical error codes.
- Ease-of-use notes from the HuleEdu consumer integration perspective.
- Cross-link to consumer-side evidence package and closure handoff note.

### Source: Validation Plan

- In Skriptoteket repo:
  - `pdm run docs-validate`
  - `pdm run pytest tests/integration --override-ini "addopts=-s -v --durations=10 --log-cli-level=INFO --import-mode=importlib"`

- In HuleEdu repo (captured as evidence links):
  - Integration tests for adapter path.
  - End-to-end smoke against Hemma tunnel/service.
  - Workload run command set over the scientific-paper corpus.

## Non-Goals

### Source: Non-goals

- No HuleEdu business-logic implementation inside Skriptoteket.
- No per-document special-case adapter paths.
- No fallback contract variants outside canonical Story 003c semantics.

## Notes

### Source: Notes

- This is a provider-side planning/validation story and should be executed in lockstep with the
  corresponding HuleEdu consumer task to support Story 003c closure.

## Decision And Assumption Ledger

The source does not provide a separate decision and assumption ledger section; no additional decision and assumption ledger is recorded.

## Plan Document Review

The source does not provide a separate plan document review section; no additional plan document review is recorded.

## Story Closeout Review

The source does not provide a separate story closeout review section; no additional story closeout review is recorded.
