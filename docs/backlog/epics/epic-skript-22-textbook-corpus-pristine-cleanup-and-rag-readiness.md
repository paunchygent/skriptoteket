---
type: epic
id: EPIC-SKRIPT-22
title: Textbook corpus pristine cleanup and RAG readiness
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
readiness_review:
  record: inline
  status: not_started
closeout_review:
  record: inline
  status: not_started
outcome: A deterministic, provenance-complete textbook corpus pipeline that preserves
  pagination/context, requires manual restoration for semantically important fixes,
  and produces trustworthy RAG-ready artifacts for PostgreSQL vector retrieval.
retired_ids:
- EPIC-22
---

## Scope

### Source: Scope

- Build a textbook-cleanup workflow where automation is strictly limited to deterministic, low-risk mechanical transforms.
- Preserve and expose provenance for every artifact and transformation step (input PDF, raw markdown, reconciled job metadata, mechanical output, manual patches, pristine output).
- Protect semantically critical content (tasks, answer keys, formulas, concept definitions) from heavy-handed automatic rewrites.
- Add a multi-agent manual restoration workflow with explicit issue ownership, verification, and reversible patching.
- Produce RAG-ready packaging with page anchors, section paths, and quality gates before embedding/vectorization.

### Source: Out of scope

- No blind auto-rewrite of ambiguous OCR spans.
- No deletion of semantically important textbook content because of formatting uncertainty.
- No direct ingestion of unresolved or unverified spans into production retrieval datasets.

## Epic Contract

The current epic outcome is: A deterministic, provenance-complete textbook corpus pipeline that preserves pagination/context, requires manual restoration for semantically important fixes, and produces trustworthy RAG-ready artifacts for PostgreSQL vector retrieval.

## ADR Coverage

The source does not record separate ADR coverage.

## Contract Inputs

### Source: Dependencies

- Sir Convert-a-Lot v2 conversion lane and job metadata semantics (EPIC-SKRIPT-21, ADR-SKRIPT-0066).
- Governance contract for script/manual separation and promotion gates (ADR-SKRIPT-0068).
- PostgreSQL vector indexing rollout used by downstream retrieval stack.

## Stories

### Source: Stories (ordered)

- [ ] 1. [ST-SKRIPT-22-01: Textbook corpus cleanup pipeline and manual restoration workflow](../stories/st-skript-22-01-textbook-corpus-cleanup-pipeline-and-manual-restoration-workflow.md)

## Epic Verification Plan

The source does not record a separate verification plan.

## Exceptions And Follow-Ups

The source records no separate approved exception or follow-up.

## Risks

### Source: Risks

- Script overreach could silently corrupt textbook meaning.
  Mitigation: hard no-autofix zones and mandatory manual queue for uncertainty.
- Parallel manual edits can produce merge collisions and inconsistent section repairs.
  Mitigation: issue-scoped patch files + second-pass verifier before apply.
- Pagination/context drift can degrade retrieval quality.
  Mitigation: explicit page anchors and integrity gates that block pristine build on drift.

## Notes

No additional current notes were recorded in the source.

## Decision And Assumption Ledger

The source does not record a separate decision and assumption ledger.

## Plan Document Review

The source does not include a plan document review record.

## Epic Closeout Review

The source does not include an epic closeout review record.
