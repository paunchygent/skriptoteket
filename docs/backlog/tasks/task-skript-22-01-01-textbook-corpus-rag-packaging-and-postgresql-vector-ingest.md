---
type: task
id: TASK-SKRIPT-22-01-01
title: Textbook corpus — RAG packaging and PostgreSQL vector ingest contract
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: ready
readiness_review:
  record: inline
  status: not_required
  approval_protocol: agent-planning:user-closure-gate
  approval_evidence: user closure 2026-07-31
closeout_review:
  record: inline
  status: not_started
story: ST-SKRIPT-22-01
task_kind: story
acceptance_criteria:
- Chunk packaging includes stable IDs, page ranges, section paths, content types,
  and hashes for every chunk.
- Vector-ingest contract supports metadata filtering and provenance traceability from
  retrieval result back to source pages.
- Retrieval QA gates over textbook tasks/answer keys block ingest promotion on quality
  failure.
---

## Context

### Problem

Even a cleaned corpus can fail in practice if chunk/provenance contracts are weak or retrieval quality is not validated.

### Goal

Produce a RAG-ready dataset and ingestion contract for PostgreSQL vector search with strict provenance and QA promotion gates.

### Non-goals

- No UI work.
- No silent acceptance of low-confidence retrieval quality.

### Implementation plan

1. Build deterministic chunker with section/page-aware boundaries.
2. Emit chunk package and ingest manifest with provenance metadata.
3. Define PostgreSQL vector indexing and metadata filtering contract.
4. Add retrieval QA set focused on textbook tasks and answer keys.
5. Enforce post-ingest DB maintenance and validation reporting.

### Test plan

- Contract tests for chunk schema and provenance completeness.
- Retrieval QA run with pass/fail threshold.
- Verify ingestion run records and stats are reproducible.

### Rollback plan

- Remove generated chunk and ingest artifacts from this slice.
- Keep pristine corpus artifact untouched.

## Decision And Assumption Ledger

The source material below remains authoritative for this section.

## Story Contract Slice

The source material below remains authoritative for this section.

## Contract Inputs

The source material below remains authoritative for this section.

## Plan

The source material below remains authoritative for this section.

## Implementation Steps

The source material below remains authoritative for this section.

## Proof

Verification expectations remain in the retained source material below.

## Validation

Verification expectations remain in the retained source material below.

## Stop Conditions

The source boundaries and recovery limits remain preserved below.

## Lessons Learned

The source material below remains authoritative for this section.

## Notes

The source material below remains authoritative for this section.

## Plan Document Review

The source material below remains authoritative for this section.

## Implementation Review

The source material below remains authoritative for this section.
