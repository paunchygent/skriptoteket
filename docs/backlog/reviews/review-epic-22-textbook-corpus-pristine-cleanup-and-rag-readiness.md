---
type: review
id: REV-EPIC-22
title: "Review: Textbook corpus pristine cleanup and RAG readiness"
status: pending
owners: "agents"
created: 2026-03-04
updated: 2026-04-06
reviewer: "lead-developer"
epic: EPIC-22
adrs:
  - ADR-0068
  - ADR-0066
stories:
  - ST-22-01
---

## TL;DR

This epic establishes a high-trust textbook corpus pipeline where deterministic scripts do only low-risk mechanical
cleanup, semantically important restoration is manual and verifier-controlled, and pristine/RAG promotion is blocked by
hard integrity and provenance gates.

## Problem Statement

Current textbook OCR output is not safe to ingest directly. If we over-automate cleanup, we risk silent corruption of
tasks, answer keys, and concept meaning. If we under-specify manual workflow, we risk inconsistent edits and weak
traceability.

## Proposed Solution

- Lock policy in ADR-0068 and execute through PR-sized tasks.
- Separate automation and manual lanes with strict no-autofix semantic zones.
- Use issue-scoped reversible patches for semantic repairs.
- Require deterministic validation before pristine and RAG ingest promotion.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0068-textbook-corpus-pristine-cleanup-and-rag-ingest-governance.md` | Policy clarity and guardrails | 10 min |
| `docs/backlog/epics/epic-22-textbook-corpus-pristine-cleanup-and-rag-readiness.md` | Scope, risks, sequencing | 6 min |
| `docs/backlog/stories/story-22-01-textbook-corpus-cleanup-pipeline-and-manual-restoration-workflow.md` | Acceptance criteria and testability | 8 min |
| `docs/backlog/prs/pr-0073-textbook-corpus-governance-immutable-snapshot-and-job-reconciliation.md` | Baseline/provenance gate completeness | 6 min |
| `docs/backlog/prs/pr-0074-textbook-corpus-deterministic-mechanical-cleanup-and-issue-ledger.md` | Script boundary enforcement | 6 min |
| `docs/backlog/prs/pr-0075-textbook-corpus-multi-agent-manual-restoration-and-verification.md` | Manual labor workflow safety | 6 min |
| `docs/backlog/prs/pr-0076-textbook-corpus-integrity-gates-and-pristine-build-contract.md` | Promotion gates and fail-closed behavior | 6 min |
| `docs/backlog/prs/pr-0077-textbook-corpus-rag-packaging-and-postgresql-vector-ingest-contract.md` | RAG provenance and retrieval QA gates | 6 min |

**Total estimated time:** ~54 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Strict no-autofix semantic zones | Prevent silent meaning corruption | [ ] |
| Manual patch + verifier workflow | Make semantic edits auditable and reversible | [ ] |
| Fail-closed pristine/RAG promotion gates | Prevent ingest of unresolved critical corruption | [ ] |

## Review Checklist

- [ ] ADR-0068 clearly separates automation and manual semantics work
- [ ] Epic/story scope is realistic and sequenced for risk reduction
- [ ] PR tasks are independently shippable and testable
- [ ] Promotion gates block unsafe corpus states
- [ ] Provenance contract is sufficient for downstream retrieval auditability

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-06
**Verdict:** pending

### Required Changes

Confirm the integrity gates, manual-restoration split, and provenance requirements before implementation starts.

### Suggestions (Optional)

Keep the deterministic mechanical cleanup lane separate from the semantic/manual restoration lane so the corpus review
stays auditable.

### Decision Approvals

- [ ] Strict no-autofix semantic zones
- [ ] Manual patch + verifier workflow
- [ ] Fail-closed pristine/RAG promotion gates

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Preserved the textbook corpus review in canonical shape while keeping the integrity/provenance decisions pending. |
