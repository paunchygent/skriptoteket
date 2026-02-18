---
type: story
id: ST-19-07
title: "Story 003c: Skriptoteket thin adapter parity + scientific PDF workload validation"
status: ready
owners: "agents"
created: 2026-02-13
epic: "EPIC-19"
dependencies:
  - "ST-19-03"
  - "RUN-huleedu-integration"
  - "EXT:sir-convert-a-lot/docs/converters/internal_adapter_contract_v1.md"
  - "EXT:sir-convert-a-lot/docs/reference/ref-story-003c-consumer-integration-handoff.md"
acceptance_criteria:
  - "Given HuleEdu integrates through the canonical Story 003c adapter contract, when requests reach Skriptoteket, then adapter handling remains thin and contract-faithful with no HuleEdu-specific logic forks in Skriptoteket."
  - "Given demanding scientific-paper PDFs are submitted from the HuleEdu integration path, when workloads execute end-to-end (submit, poll, retrieve), then outcomes are surfaced via canonical status and structured error surfaces without per-document code changes."
  - "Given a representative scientific-paper corpus is executed, when validation completes, then evidence includes per-document status, duration distribution (min/p50/p95/max), and failure taxonomy mapped to canonical error codes."
  - "Given Story 003c closure review, when reviewers inspect Skriptoteket docs, then this story and linked evidence clearly support closure readiness from the provider side."
ui_impact: "No (integration/provider behavior + validation evidence)"
data_impact: "No (evidence artifacts and docs updates only)"
---

## Context

This story is the Skriptoteket-side parallel to HuleEdu consumer adoption work for Story 003c.
The goal is to prove the provider side remains easy to consume for demanding scientific-paper PDF
workloads without introducing consumer-specific branches in Skriptoteket.

## Scope

- Align/confirm Skriptoteket adapter behavior against canonical Story 003c contract semantics.
- Validate the end-to-end consumer path from HuleEdu against Skriptoteket service surfaces.
- Capture provider-side workload evidence for a representative demanding scientific-paper corpus.
- Publish closure-ready evidence links in Skriptoteket docs.

## Non-goals

- No HuleEdu business-logic implementation inside Skriptoteket.
- No per-document special-case adapter paths.
- No fallback contract variants outside canonical Story 003c semantics.

## Workload Validation Requirements

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

## Evidence Package

- Per-document status summary.
- Duration distribution summary (min/p50/p95/max).
- Failure taxonomy mapped to canonical error codes.
- Ease-of-use notes from the HuleEdu consumer integration perspective.
- Cross-link to consumer-side evidence package and closure handoff note.

## Validation Plan

- In Skriptoteket repo:
  - `pdm run docs-validate`
  - `pdm run pytest tests/integration --override-ini "addopts=-s -v --durations=10 --log-cli-level=INFO --import-mode=importlib"`

- In HuleEdu repo (captured as evidence links):
  - Integration tests for adapter path.
  - End-to-end smoke against Hemma tunnel/service.
  - Workload run command set over the scientific-paper corpus.

## Notes

- This is a provider-side planning/validation story and should be executed in lockstep with the
  corresponding HuleEdu consumer task to support Story 003c closure.
