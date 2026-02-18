---
type: pr
id: PR-0061
title: "Story 003c: thin adapter parity and demanding scientific PDF workload validation"
status: ready
owners: "agents"
created: 2026-02-13
updated: 2026-02-13
stories:
  - "ST-19-07"
tags: ["backend", "integration", "huledu", "workload-validation"]
acceptance_criteria:
  - "Skriptoteket provider-side adapter behavior is verified against canonical Story 003c contract semantics, with no HuleEdu-specific logic forks."
  - "End-to-end HuleEdu consumer flow (submit, poll, retrieve) runs against Skriptoteket without per-document converter code changes."
  - "Demanding scientific-paper workload evidence is produced with per-document status, duration distribution (min/p50/p95/max), and failure taxonomy mapped to canonical error codes."
  - "Story/PR docs link to provider + consumer evidence artifacts sufficient to support Story 003c closure review."
---

## Problem

Story 003c closure requires proof that the provider side (Skriptoteket) remains contract-faithful and
easy to consume from HuleEdu for demanding scientific-paper PDF workloads. Existing artifacts do not
yet provide a closure-ready, cross-repo evidence package.

## Goal

- Validate Skriptoteket thin-adapter behavior against canonical Story 003c semantics.
- Demonstrate consumer ergonomics from HuleEdu with no per-document special cases.
- Produce a reproducible evidence package for demanding scientific-paper corpus runs.
- Link evidence into docs for closure readiness.

## Non-goals

- Implementing HuleEdu business logic inside Skriptoteket.
- Introducing fallback contract variants or compatibility shims.
- Per-document converter code edits to complete the workload.

## Implementation plan

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

## Test plan

- Skriptoteket repo:
  - `pdm run docs-validate`
  - `pdm run pytest tests/integration --override-ini "addopts=-s -v --durations=10 --log-cli-level=INFO --import-mode=importlib"`
- HuleEdu repo:
  - adapter-path integration tests
  - end-to-end smoke against Hemma tunnel/service
  - workload execution commands for the scientific-paper corpus

## Rollback plan

- Revert documentation artifacts (`PR-0061`, any linked story/epic note edits) if scope or contract target changes.
- Keep runtime behavior unchanged unless explicitly modified in follow-up implementation PRs.
