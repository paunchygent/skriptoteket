---
type: review
id: REV-EPIC-21
title: "Review: Curated app - Conversion Hub (Sir Convert-a-Lot v2)"
status: pending
owners: "agents"
created: 2026-03-01
reviewer: "lead-developer"
epic: EPIC-21
adrs:
  - ADR-0066
stories:
  - ST-21-01
  - ST-21-02
---

## TL;DR

Replace Skriptoteket's production `html-to-pdf-preview` script tool with a first-class curated app that provides a
complete conversion UI and routes all supported conversions through Sir Convert-a-Lot v2 (batch + preview included).

## Problem Statement

Skriptoteket currently relies on a dynamic script tool (`html-to-pdf-preview`) as a production conversion surface.
This duplicates capabilities, hardcodes an interaction flow, and blurs the product strategy for downstream products.

## Proposed Solution

- Adopt Sir Convert-a-Lot v2 as the canonical conversion engine (ADR-0066).
- Ship a bespoke-required curated app ("Conversion Hub") that orchestrates v2 jobs (submit/poll/download) and provides
  batch conversion UX.
- Retire `html-to-pdf-preview` from production seeding and migrate tests to the curated app surface.

## Artifacts to Review

| File | Focus | Time |
|------|-------|------|
| `docs/adr/adr-0066-sir-convert-a-lot-v2-as-canonical-conversion-engine.md` | Decision clarity + consequences | 8 min |
| `docs/backlog/epics/epic-21-curated-app-conversion-hub.md` | Scope in/out + ordering | 6 min |
| `docs/backlog/stories/story-21-01-curated-app-conversion-hub-v1.md` | Acceptance criteria + UX/testability | 6 min |
| `docs/backlog/stories/story-21-02-migrate-off-html-to-pdf-preview-and-retire-tool.md` | Migration plan + test updates | 6 min |

**Total estimated time:** ~26 minutes

## Key Decisions

| Decision | Rationale | Approve? |
|----------|-----------|----------|
| Curated app is canonical conversion UI (no tool-script fallback) | Avoid duplicate conversion lanes and legacy slop | [ ] |
| Batch conversion = N independent v2 jobs (per-file status) | Keeps semantics simple and UI-friendly | [ ] |
| Preview = normal v2 job producing normal PDF artifact | Avoid special preview engine/routes | [ ] |

## Review Checklist

- [ ] ADR-0066 locks the strategy clearly (and forbids legacy/shims)
- [ ] EPIC scope is crisp and PR tasks are realistically sized
- [ ] Stories have testable acceptance criteria and cover batch + preview
- [ ] Migration plan updates E2E/unit tests without weakening coverage
- [ ] Risks have explicit mitigations (timeouts, error surfaces, artifact assertions)
