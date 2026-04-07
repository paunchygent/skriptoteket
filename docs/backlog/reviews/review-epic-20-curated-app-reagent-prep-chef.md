---
type: review
id: REV-EPIC-20
title: "Review: Curated app — Reagent Prep Chef"
status: pending
owners: "agents"
created: 2026-01-26
updated: 2026-04-06
reviewer: "lead-developer"
epic: EPIC-20
adrs:
  - ADR-0022
  - ADR-0023
  - ADR-0024
  - ADR-0067
stories:
  - ST-20-01
  - ST-20-02
  - ST-20-03
---

## TL;DR

EPIC-20 ships a teacher-first, backend-native curated app for chemistry lab prep: deterministic scaling (groups/volume),
hydrate-aware molar mass calculation, purity/dilution support, and curated-only safety output with SDS fallback. It uses
the existing curated apps execution path and Tool UI contract v2, with no new DB migrations.

## Problem Statement

High school chemistry prep frequently fails on logistics and unit handling (hydration state, purity, dilution math).
Teachers need a fast, reliable prep sheet with explicit safety posture and minimal UI friction.

## Proposed Solution

- Implement **Reagent Prep Chef** as a curated app (ADR-0023) executed in trusted backend code (no runner).
- Render a typed form + results via Tool UI contract v2 (ADR-0022) and persist state/ui_payload via ADR-0024.
- Use a repo-owned hazards dataset for curated safety lookups and explicitly fall back to “Consult SDS”.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/reference/ref-curated-app-reagent-prep-chef.md` | UX + safety posture + math outline | 12 min |
| `docs/backlog/epics/epic-20-curated-app-reagent-prep-chef.md` | Scope + risks | 4 min |
| `docs/backlog/stories/story-20-01-curated-app-reagent-prep-chef.md` | Testable acceptance criteria | 5 min |
| `docs/adr/adr-0022-tool-ui-contract-v2.md` | Output/action/state constraints | 6 min |
| `docs/adr/adr-0023-curated-apps-registry-and-execution.md` | Execution path + catalog integration | 6 min |
| `docs/adr/adr-0024-tool-sessions-and-ui-payload-persistence.md` | State persistence semantics | 8 min |

**Total estimated time:** ~41 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| UI policy: `bespoke_required` vs `generic_ok` | Avoid dead routes while still enforcing bespoke UX where required | [ ] |
| Curated-only hazards (no heuristics) | Avoid false confidence | [ ] |
| Formula mass dependency choice (e.g. `molmass`) | Robust parsing vs build size | [ ] |
| Export format (PDF artifact) | Printability + consistent sharing | [ ] |

## Review Checklist

- [ ] Safety posture prevents false confidence
- [ ] Scope stays within “solution prep” (no synthesis guidance)
- [ ] Acceptance criteria are testable and match platform constraints
- [ ] Dependency choice is reasonable for prod images
- [ ] Risks are identified with mitigations

## Review Feedback

**Reviewer:** lead-developer
**Date:** 2026-04-06
**Verdict:** pending

### Required Changes

Confirm the safety posture, PDF/export shape, and dependency tradeoffs before implementation starts.

### Suggestions (Optional)

Keep the app-specific UX and the safety fallback contract explicit so the review stays reviewable.

### Decision Approvals

- [ ] Safety posture prevents false confidence
- [ ] Scope stays within "solution prep"
- [ ] Acceptance criteria are testable and match platform constraints

## Changes Made

| Change | Artifact | Description |
|--------|----------|-------------|
| 1 | Review record | Kept the curated-app proposal in canonical review shape while leaving the core EPIC-20 decisions pending. |
