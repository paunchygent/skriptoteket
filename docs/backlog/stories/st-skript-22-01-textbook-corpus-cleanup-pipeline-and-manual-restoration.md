---
type: story
id: ST-SKRIPT-22-01
title: Textbook corpus cleanup pipeline and manual restoration workflow
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
epic: EPIC-SKRIPT-22
acceptance_criteria:
- Given textbook conversion artifacts exist, when the baseline is prepared, then immutable
  raw artifacts + checksums + reconciled terminal job states are stored before cleanup
  starts.
- Given script cleanup runs, when output is generated, then only deterministic mechanical
  transforms are applied and all ambiguous/semantic regions are emitted to a manual
  restoration queue.
- Given semantically important sections (tasks, answer keys, formulas, definitions),
  when changes are made, then edits are manual and reversible with issue-scoped patch
  metadata and a second-pass verifier.
- Given a pristine corpus build is requested, when validators run, then section continuity,
  task numbering, answer-key mapping, page-anchor integrity, and unresolved-critical-issue
  checks all pass.
- Given RAG packaging is generated, when chunks are emitted, then each chunk includes
  stable provenance (page range, section path, content type, hash) suitable for PostgreSQL
  vector indexing and auditability.
- Given retrieval QA is executed against textbook tasks/answer keys, when quality
  thresholds fail, then ingest promotion is blocked and unresolved issues remain explicit.
retired_ids:
- ST-22-01
---

## Context

Current textbook OCR markdown contains structural and semantic corruption patterns that cannot be safely fixed by one-shot automation. We need a strict boundary:

- scripts for deterministic mechanics,
- humans/subagents for semantically meaningful restoration,
- hard quality gates before RAG ingestion.

## Epic Contract Slice

- Reconcile long-job manifest drift so local corpus state matches server terminal status.
- Build deterministic script-based cleanup for mechanical issues only.
- Build multi-agent manual restoration workflow with reviewer verification.
- Build integrity gates and pristine output contract.
- Build RAG-ready packaging and ingestion validation contract.

## ADR Coverage

No separate material is recorded in the source snapshot.

## Contract Inputs

No separate material is recorded in the source snapshot.

## Live Verification Plan

No separate material is recorded in the source snapshot.

## Non-Goals

- No heuristic auto-content reconstruction in semantically important spans.
- No direct vector ingest from raw or unresolved markdown.

## Notes

### Context

Current textbook OCR markdown contains structural and semantic corruption patterns that cannot be safely fixed by one-shot automation. We need a strict boundary:

- scripts for deterministic mechanics,
- humans/subagents for semantically meaningful restoration,
- hard quality gates before RAG ingestion.

### Scope

- Reconcile long-job manifest drift so local corpus state matches server terminal status.
- Build deterministic script-based cleanup for mechanical issues only.
- Build multi-agent manual restoration workflow with reviewer verification.
- Build integrity gates and pristine output contract.
- Build RAG-ready packaging and ingestion validation contract.

### Non-goals

- No heuristic auto-content reconstruction in semantically important spans.
- No direct vector ingest from raw or unresolved markdown.

### PR Tasks (ordered)

- [x] 1. PR-0073: Governance + immutable snapshot + job reconciliation gate
- [x] 2. PR-0074: Deterministic mechanical cleanup + issue ledger + manual queue generation
- [x] 3. PR-0075: Multi-agent manual restoration workflow + reversible patch application
- [x] 4. PR-0076: Integrity gates + pristine corpus build contract
- [ ] 5. PR-0077: RAG packaging + PostgreSQL vector ingest contract + retrieval QA gates

### Working Model

- Automation does less, but does it deterministically and audibly.
- Manual restoration does the semantically hard work and is the preferred lane for meaning-preserving fixes.
- No corpus is promoted to embedding without passing integrity and provenance gates.

## Decision And Assumption Ledger

The source snapshot is the governing record for the decisions and assumptions stated above.

## Plan Document Review

No separate material is recorded in the source snapshot.

## Story Closeout Review

No separate material is recorded in the source snapshot.
