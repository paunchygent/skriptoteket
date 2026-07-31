---
type: adr
id: ADR-SKRIPT-0068
title: 'Textbook corpus: pristine cleanup and RAG ingest governance'
repository: skriptoteket
owners:
- kind: service
  id: skriptoteket
created: '2026-07-31'
status: proposed
links:
  governing:
  - EPIC-SKRIPT-22
  - ST-SKRIPT-22-01
  - TASK-SKRIPT-22-01-01
deciders:
- user-lead
retired_ids:
- ADR-0068
---

## Context

### Source: Context

Textbook OCR conversion output contains both mechanical defects and semantically important corruption in tasks,
answer keys, formulas, and section continuity.

A script-first cleanup that attempts to auto-correct everything is high risk and can silently damage meaning.
At the same time, fully manual end-to-end cleanup is too slow without deterministic preprocessing and issue triage.

The corpus will be embedded and indexed for retrieval. This makes provenance and trust requirements stricter:

- every retrieval chunk must be traceable to source pages,
- unresolved or ambiguous spans must not be silently promoted,
- ingest quality must be validated before vector promotion.

## Decision

### Source: Decision

### 1) Adopt a two-lane cleanup model with strict boundaries

- **Automation lane**: deterministic mechanical transforms only.
- **Manual lane**: semantically meaningful restoration via issue-scoped patches and verifier approval.

### 2) Enforce no-autofix semantic zones

Scripts must not auto-rewrite ambiguous spans in:

- exercise/task statements,
- answer keys/solution text,
- formulas/chemical expressions,
- concept definitions where wording changes meaning.

Any uncertainty in these zones must be emitted to a manual queue.

### 3) Require immutable provenance snapshots before cleanup

Before any cleanup:

- snapshot raw PDF + raw markdown + manifests,
- reconcile non-terminal local job states against server terminal states,
- persist checksums and job/result metadata snapshots.

### 4) Require reversible manual restoration workflow

Semantic changes are applied only through structured patch files with:

- source span references,
- rationale,
- reviewer verification,
- deterministic apply/revert behavior.

No direct bulk editing of the pristine target artifact is allowed.

### 5) Gate pristine and RAG promotion with hard validators

Pristine promotion is blocked unless integrity checks pass:

- section continuity,
- page-anchor continuity,
- task numbering continuity,
- answer-key mapping coverage,
- no unresolved critical issues.

RAG ingest promotion is blocked unless chunk provenance and retrieval QA thresholds pass.

### 6) PostgreSQL vector contract

RAG chunk packages must include stable provenance fields (page range, section path, content type, hashes) and support
metadata-filtered vector retrieval.

Operationally, post-load planner stats maintenance is required (`ANALYZE`/`VACUUM ANALYZE`) before performance claims.

## Non-Decisions

The source records no separate non-decision section; adjacent boundaries remain part of the selected decision.

## Consequences

### Source: Consequences

- Lower risk of semantic corruption from aggressive scripts.
- More manual effort for semantically important repairs (intentional).
- Better auditability and rollback via deterministic transforms and reversible patch artifacts.
- Cleaner downstream retrieval behavior because unresolved ambiguity is explicit and blocked from promotion.
