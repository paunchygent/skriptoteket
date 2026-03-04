---
type: epic
id: EPIC-22
title: "Textbook corpus pristine cleanup and RAG readiness"
status: proposed
owners: "agents"
created: 2026-03-04
outcome: "A deterministic, provenance-complete textbook corpus pipeline that preserves pagination/context, requires manual restoration for semantically important fixes, and produces trustworthy RAG-ready artifacts for PostgreSQL vector retrieval."
---

## Scope

- Build a textbook-cleanup workflow where automation is strictly limited to deterministic, low-risk mechanical transforms.
- Preserve and expose provenance for every artifact and transformation step (input PDF, raw markdown, reconciled job metadata, mechanical output, manual patches, pristine output).
- Protect semantically critical content (tasks, answer keys, formulas, concept definitions) from heavy-handed automatic rewrites.
- Add a multi-agent manual restoration workflow with explicit issue ownership, verification, and reversible patching.
- Produce RAG-ready packaging with page anchors, section paths, and quality gates before embedding/vectorization.

## Out of scope

- No blind auto-rewrite of ambiguous OCR spans.
- No deletion of semantically important textbook content because of formatting uncertainty.
- No direct ingestion of unresolved or unverified spans into production retrieval datasets.

## Stories (ordered)

- [ ] 1. [ST-22-01: Textbook corpus cleanup pipeline and manual restoration workflow](../stories/story-22-01-textbook-corpus-cleanup-pipeline-and-manual-restoration-workflow.md)

## Risks

- Script overreach could silently corrupt textbook meaning.
  Mitigation: hard no-autofix zones and mandatory manual queue for uncertainty.
- Parallel manual edits can produce merge collisions and inconsistent section repairs.
  Mitigation: issue-scoped patch files + second-pass verifier before apply.
- Pagination/context drift can degrade retrieval quality.
  Mitigation: explicit page anchors and integrity gates that block pristine build on drift.

## Dependencies

- Sir Convert-a-Lot v2 conversion lane and job metadata semantics (EPIC-21, ADR-0066).
- PostgreSQL vector indexing rollout used by downstream retrieval stack.
